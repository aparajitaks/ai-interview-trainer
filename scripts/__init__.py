"""scripts package init.

This file is intentionally minimal: running `python -m scripts.test_preprocessing`
from the repository root will have the project root on sys.path[0], so absolute
imports like `from preprocessing.video_to_frames import ...` will resolve.

If a user imports `scripts` from another location, we avoid mutating sys.path
here to prevent side-effects.
"""

__all__ = ["test_preprocessing"]
