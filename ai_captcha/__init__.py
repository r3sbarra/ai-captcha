"""AI CAPTCHA — reverse-CAPTCHA challenge app.

Proves you're an AI, not a human. Serves a timed series of puzzles that are
trivial for a capable model but near-impossible for a human under the clock.

Runs standalone, as an AppManager sub-app, or embedded in any Flask project.
"""

__version__ = "1.0.0"

from .app import create_app, init_app, blueprint
from .manifest import manifest

__all__ = ["create_app", "init_app", "blueprint", "manifest", "__version__"]
