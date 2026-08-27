"""Standalone dev server for AI CAPTCHA."""

from ai_captcha import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100, debug=True)
