from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

# Storage abstraction placeholder.
# For MVP, frame URLs can be data URLs or already-hosted URLs from frontend.


def normalize_frame_url(frame_url: str | None) -> str | None:
    if not frame_url:
        return None
    return frame_url.strip()


def load_starter_frame_data_url() -> str | None:
    configured = os.getenv("STARTER_IMAGE_PATH", "").strip()
    if configured:
        image_path = Path(configured)
    else:
        image_path = Path(__file__).resolve().parents[2] / "assets" / "starter.png"

    if not image_path.exists() or not image_path.is_file():
        return None

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/png"

    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"
