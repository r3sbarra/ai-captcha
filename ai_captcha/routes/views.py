"""Web UI blueprint — human-facing pages to watch AI attempts."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from ..engine.gating import TIER_ORDER

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    return render_template("index.html", tiers=TIER_ORDER)


@views_bp.route("/challenge")
def challenge():
    return render_template("challenge.html")


@views_bp.route("/results")
def results():
    return render_template("results.html")


@views_bp.route("/failed")
def failed():
    from flask import current_app

    return render_template(
        "failed.html",
        redirect_url=current_app.config.get("FAILED_REDIRECT_URL", "/"),
        redirect_seconds=current_app.config.get("FAILED_REDIRECT_SECONDS", 7),
    )


@views_bp.route("/docs")
def docs():
    return render_template("docs.html")


@views_bp.route("/embed-demo")
def embed_demo():
    from flask import current_app

    return render_template(
        "embed_demo.html",
        base_path=current_app.config.get("APPLICATION_ROOT", "") or request.script_root.rstrip("/"),
    )


@views_bp.route("/benchmark")
def benchmark():
    from ..benchmark_results import load_benchmark

    return render_template("benchmark.html", bench=load_benchmark())


@views_bp.route("/mission")
def mission():
    return render_template("mission.html")
