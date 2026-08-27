"""Pluggable cache abstraction for AI CAPTCHA.

AI CAPTCHA needs a small, fast key-value store for:

* **Rate limiting** — per-IP / per-session token buckets.
* **Replay protection** — a denylist of consumed ``jti`` nonces until token expiry.
* **Optional session state** — ephemeral data that doesn't need to persist in the DB.

The design is dependency-free by default: a **memory** cache (perfect for
single-process dev/standalone) and a **file** cache (survives restarts, works
on PythonAnywhere where threads and Redis are limited) are included.

To plug in an existing popular cache (Redis, Memcached, etc.), pass a
``CACHE_BACKEND`` that is either:

* a **callable/class** taking no args returning an object with the cache API, or
* an **instance** with the same API.

The cache API is deliberately minimal (the intersection of most caches):

* ``get(key) -> value | None``
* ``set(key, value, ttl_seconds=None) -> None``
* ``incr(key, delta=1, ttl_seconds=None) -> int``
* ``delete(key) -> None``

When embedding, you may also set ``app.config["CACHE_BACKEND"]`` to an existing
instance (e.g. a Flask-Caching / django-redis client) and AI CAPTCHA will use it
as-is. See ``docs/embedding.md``.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    """Minimal cache interface used throughout AI CAPTCHA."""

    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None: ...
    def incr(self, key: str, delta: int = 1, ttl_seconds: int | None = None) -> int: ...
    def delete(self, key: str) -> None: ...


class MemoryCache:
    """Thread-safe in-process cache. Default backend.

    Keys are namespaced to avoid collisions with other components sharing the
    same cache object. Values are held in memory; lost on process restart.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.Lock()

    def _ns(self, key: str) -> str:
        return f"ai_captcha::{key}"

    def _purge_locked(self, now: float) -> None:
        for k, (_, exp) in list(self._store.items()):
            if exp is not None and exp <= now:
                del self._store[k]

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            self._purge_locked(now)
            item = self._store.get(self._ns(key))
            if item is None:
                return None
            value, exp = item
            if exp is not None and exp <= now:
                del self._store[self._ns(key)]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        now = time.monotonic()
        exp = now + ttl_seconds if ttl_seconds is not None else None
        with self._lock:
            self._purge_locked(now)
            self._store[self._ns(key)] = (value, exp)

    def incr(self, key: str, delta: int = 1, ttl_seconds: int | None = None) -> int:
        now = time.monotonic()
        ns = self._ns(key)
        with self._lock:
            self._purge_locked(now)
            item = self._store.get(ns)
            if item is None:
                exp = now + ttl_seconds if ttl_seconds is not None else None
                self._store[ns] = (delta, exp)
                return delta
            value, exp = item
            if exp is not None and exp <= now:
                exp = now + ttl_seconds if ttl_seconds is not None else None
                self._store[ns] = (delta, exp)
                return delta
            new = value + delta
            self._store[ns] = (new, exp)
            return new

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(self._ns(key), None)


class FileCache:
    """Simple file-based cache. Survives restarts; works without threads/Redis.

    Each key is a file under a cache directory. Values are JSON-serialized.
    Good for PythonAnywhere and single-node deployments. Not for high
    throughput, but correct and dependency-free.
    """

    def __init__(self, directory: str | None = None) -> None:
        if directory is None:
            base = os.getenv("AIC_CACHE_DIR", "")
            if base:
                directory = base
            else:
                # Default: instance/cache, or a temp dir if that isn't writable.
                from ..config import _DEFAULT_INSTANCE
                candidate = Path(_DEFAULT_INSTANCE) / "cache"
                try:
                    candidate.mkdir(parents=True, exist_ok=True)
                    probe = candidate / ".probe"
                    probe.touch()
                    probe.unlink()
                    directory = str(candidate)
                except OSError:
                    directory = tempfile.mkdtemp(prefix="ai_captcha_cache_")
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, key: str) -> Path:
        # Keys are assumed safe (no path separators) — sanitize defensively.
        safe = key.replace("/", "_").replace("\\", "_").replace("..", "_")
        return self._dir / f"{safe}.json"

    def _read(self, path: Path):
        try:
            import json

            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("exp") is not None and data["exp"] <= time.time():
                self.delete(path.stem)
                return None
            return data.get("value")
        except (OSError, ValueError):
            return None

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._read(self._path(key))

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        import json

        exp = time.time() + ttl_seconds if ttl_seconds is not None else None
        with self._lock:
            try:
                with open(self._path(key), "w", encoding="utf-8") as fh:
                    json.dump({"value": value, "exp": exp}, fh)
            except OSError:
                pass

    def incr(self, key: str, delta: int = 1, ttl_seconds: int | None = None) -> int:
        import json

        path = self._path(key)
        with self._lock:
            cur = self._read(path)
            new = (cur or 0) + delta
            exp = time.time() + ttl_seconds if ttl_seconds is not None else None
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump({"value": new, "exp": exp}, fh)
            except OSError:
                pass
            return new

    def delete(self, key: str) -> None:
        with self._lock:
            try:
                self._path(key).unlink(missing_ok=True)
            except OSError:
                pass


# Supported built-in backend names.
BUILTIN_BACKENDS = {
    "memory": MemoryCache,
    "file": FileCache,
}


def get_cache(app) -> Cache:
    """Return the configured cache instance for ``app``.

    Resolution order:

    1. ``app.extensions["ai_captcha_cache"]`` — set explicitly (e.g. when the
       embedder wires their own client). Return as-is.
    2. ``app.config["CACHE_BACKEND"]`` —
       * an instance with the cache API → used as-is (plug in Redis/etc.),
       * a class/callable with no required args → instantiated,
       * a string name in ``BUILTIN_BACKENDS`` → built-in,
       * a dotted import path ``"pkg.mod:Class"`` → imported + instantiated.
    3. Fallback: ``MemoryCache``.

    The cache is cached on the app extension so it's created once.
    """
    existing = app.extensions.get("ai_captcha_cache")
    if existing is not None:
        return existing

    backend = app.config.get("CACHE_BACKEND", "memory")
    cache = _resolve_backend(backend)
    app.extensions["ai_captcha_cache"] = cache
    return cache


def _resolve_backend(backend: Any) -> Cache:
    if isinstance(backend, Cache) or hasattr(backend, "get") and hasattr(backend, "set"):
        return backend  # already an instance
    if isinstance(backend, str):
        name = backend.strip().lower()
        if name in BUILTIN_BACKENDS:
            return BUILTIN_BACKENDS[name]()
        # dotted path "pkg.module:Class"
        if ":" in backend:
            mod_path, cls_name = backend.split(":", 1)
            import importlib

            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            return cls()
        # A named external backend string we can't resolve → fall back to memory.
        return MemoryCache()
    if callable(backend):
        return backend()
    return MemoryCache()


def make_key(parts: list[str]) -> str:
    """Build a namespaced cache key from parts."""
    return ":".join(str(p) for p in parts)
