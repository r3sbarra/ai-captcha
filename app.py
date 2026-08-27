"""AppManager entrypoint — re-exports the Flask app from the ai_captcha package.

AppManager's loader imports this file as ``appmanager.installed.ai-captcha.app``
and reads the ``app`` attribute (a Flask instance).
"""

from ai_captcha import create_app

app = create_app()
