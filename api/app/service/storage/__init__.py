"""Where an item's audio and images live, and how they are served back.

Callers use `audio_storage` and `image_storage`. Both are chosen once from configuration at
import time, so which backend is in play is never a branch in a route (invariant 6). The
concrete classes and the factories stay behind the submodules.
"""

from .audio import audio_ext, build_audio_storage
from .image import build_image_storage

audio_storage = build_audio_storage()
image_storage = build_image_storage()

__all__ = ["audio_ext", "audio_storage", "image_storage"]
