"""Example: embed AI CAPTCHA into an existing Flask project.

This shows the two embedding styles:

1. ``init_app(app)`` — registers the blueprint + DB in one call.
2. ``app.register_blueprint(blueprint)`` — register the routes yourself and
   manage the DB separately.

Run with::

    python examples/embed_example.py
"""

from __future__ import annotations

from flask import Flask, jsonify

# Style 1: full embed (blueprint + DB).
from ai_captcha import init_app

app = Flask(__name__)
app.config["SECRET_KEY"] = "my-app-secret"
app.config["TOKEN_SECRET"] = "my-app-secret"  # used to sign/verify captcha tokens
init_app(app)


# Protect a route with the decorators.
from ai_captcha.decorators import ai_captcha_required, tier_gate


@app.route("/api/secret")
@tier_gate("hard")
@ai_captcha_required
def secret():
    return jsonify({"data": "only verified robots see this"})


@app.route("/")
def home():
    return jsonify({"message": "AI CAPTCHA embedded example. Try /api/secret and /api/start"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5200, debug=True)
