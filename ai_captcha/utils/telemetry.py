"""Optional AppManager telemetry bridge.

When running under AppManager, ``appmanager.bridge`` is importable and events
are reported to the host. When standalone or embedded, these calls silently
no-op.
"""

from __future__ import annotations

from typing import Any


def report_event(event_type: str, data: dict[str, Any] | None = None) -> None:
    try:
        from appmanager.bridge import report_event as _bridge_report

        _bridge_report("ai-captcha", event_type, data)
    except ImportError:
        pass


def report_metric(metric_name: str, value: Any) -> None:
    try:
        from appmanager.bridge import report_metric as _bridge_metric

        _bridge_metric("ai-captcha", metric_name, value)
    except ImportError:
        pass
