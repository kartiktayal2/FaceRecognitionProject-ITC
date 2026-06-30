# =============================================================================
# detectors/smoking_detector.py
# ITC Customer Analytics — Smoking / Cigarette Detection Module
#
# Responsibility:
#   Accept an OpenCV frame (numpy array), send it to the Roboflow
#   Serverless API, parse the response, and return a clean list of
#   detection dicts.
#
# Public API (the only symbol app.py should import):
#   detect(frame: np.ndarray) -> list[dict]
#
# Swap guide (replacing with a local YOLO model later):
#   1. Remove the Roboflow client init block.
#   2. Load your local YOLO model at module level.
#   3. Rewrite _run_inference(frame) to call model.predict() instead.
#   4. Keep _parse_detections() or replace it with your own parser.
#   5. The detect() signature and return format stay identical —
#      no changes needed anywhere in app.py.
# =============================================================================

import os
import io
import logging

import cv2
import numpy as np
from PIL import Image

# =============================================================================
# LOGGING
# Uses the Flask-compatible root logger so messages appear in the Flask console.
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# ROBOFLOW CLIENT INITIALISATION
#
# The API key is read from the environment variable ROBOFLOW_API_KEY.
# Set it in your shell or .env file before starting the Flask server:
#
#   export ROBOFLOW_API_KEY="your_key_here"
#
# Keeping the key out of source code avoids accidental commits.
#
# MODEL_ID targets version 2 of the "smoking_person" workspace model.
# To switch to a different model version, update MODEL_ID only.
# =============================================================================

MODEL_ID   = "smoking_person/2"
API_URL    = "https://serverless.roboflow.com"

# Confidence threshold (0.0 – 1.0).
# Detections below this value are silently discarded.
# Raise it to reduce false positives; lower it to catch more cases.
CONFIDENCE_THRESHOLD = 0.40

# Seconds to wait for a response from the Roboflow API before giving up.
# Keep this value below your camera frame interval to avoid frame queuing.
API_TIMEOUT_SECONDS = 5

# --------------------------------------------------------------------------
# Lazy-initialise the client so an import error doesn't crash the entire
# Flask application if inference_sdk is not installed.
# --------------------------------------------------------------------------
_client = None


def _get_client():
    """
    Return the cached InferenceHTTPClient, creating it on first call.
    Returns None if the SDK is unavailable or the API key is missing.
    """
    global _client

    if _client is not None:
        return _client

    # ── Dependency check ──────────────────────────────────────────────────
    try:
        from inference_sdk import InferenceHTTPClient
    except ImportError:
        logger.error(
            "[smoking_detector] inference_sdk is not installed. "
            "Run:  pip install inference-sdk"
        )
        return None

    # ── API key check ─────────────────────────────────────────────────────
    api_key = "qvGo7r4z2dX0UCgcoDF4"
    if not api_key:
        logger.error(
            "[smoking_detector] ROBOFLOW_API_KEY environment variable is not set. "
            "Smoking detection is disabled."
        )
        return None

    # ── Create and cache the client ───────────────────────────────────────
    try:
        _client = InferenceHTTPClient(
            api_url=API_URL,
            api_key=api_key,
        )
        print("✅ Roboflow client created")
        logger.info(
            "[smoking_detector] Roboflow client initialised. "
            f"Model: {MODEL_ID}  |  Confidence threshold: {CONFIDENCE_THRESHOLD}"
        )
    except Exception as exc:
        logger.error(f"[smoking_detector] Failed to create Roboflow client: {exc}")
        _client = None

    return _client


# =============================================================================
# INTERNAL — frame conversion
# =============================================================================

def _frame_to_pil(frame: np.ndarray) -> Image.Image:
    """
    Convert an OpenCV BGR numpy array to a PIL RGB Image.
    Roboflow's SDK accepts PIL Images directly, which avoids a
    temporary file write and keeps the pipeline in memory.
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


# =============================================================================
# INTERNAL — API call
#
# ⚠ PERFORMANCE NOTE:
#   This function makes a synchronous HTTP request to the Roboflow
#   Serverless API. Round-trip latency (typically 150 – 600 ms depending
#   on network and server load) will reduce the effective FPS of your
#   camera stream if called on every frame.
#
#   Recommended strategies to mitigate this:
#     1. Run detect() only every N frames (e.g. every 5th frame).
#     2. Move detect() to a background thread or asyncio task and overlay
#        the last known detections on intermediate frames.
#     3. Switch to a local YOLO model (see swap guide at the top of this file)
#        to eliminate network latency entirely.
# =============================================================================

def _run_inference(frame: np.ndarray) -> dict | None:
    """
    Send *frame* to the Roboflow API and return the raw response dict.
    Returns None on any error so the caller can fall back gracefully.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        pil_image = _frame_to_pil(frame)

        # ── API REQUEST — latency occurs here ────────────────────────────
        print("Sending frame to Roboflow...")
        raw_result = client.infer(pil_image, model_id=MODEL_ID)
        
        # ─────────────────────────────────────────────────────────────────

        return raw_result

    except TimeoutError:
        logger.warning("[smoking_detector] API request timed out — skipping frame.")
        return None

    except ConnectionError:
        logger.warning("[smoking_detector] Network unavailable — skipping frame.")
        return None

    except Exception as exc:
        logger.error(f"[smoking_detector] Unexpected API error: {exc}")
        return None


# =============================================================================
# INTERNAL — response parser
#
# Roboflow Serverless responses follow this shape:
# {
#   "predictions": [
#     {
#       "class":      "Smoking",
#       "confidence": 0.95,
#       "x":          320.0,   ← centre x
#       "y":          180.0,   ← centre y
#       "width":      120.0,
#       "height":     160.0
#     },
#     ...
#   ]
# }
#
# If Roboflow ever changes their response schema, only this function
# needs updating — detect() and app.py stay unchanged.
# =============================================================================

def _parse_detections(raw: dict) -> list[dict]:
    """
    Convert a raw Roboflow response dict into a clean list of detection dicts.

    Each returned dict contains:
        label      (str)   — class name, e.g. "Smoking"
        confidence (float) — 0.0 – 1.0
        x          (int)   — bounding box centre x (pixels)
        y          (int)   — bounding box centre y (pixels)
        width      (int)   — bounding box width (pixels)
        height     (int)   — bounding box height (pixels)

    Detections below CONFIDENCE_THRESHOLD are filtered out.
    Returns [] if the response is empty or malformed.
    """
    if not isinstance(raw, dict):
        logger.warning(f"[smoking_detector] Unexpected response type: {type(raw)}")
        return []

    predictions = raw.get("predictions", [])

    if not isinstance(predictions, list):
        logger.warning("[smoking_detector] 'predictions' field is not a list.")
        return []

    results = []

    for pred in predictions:
        try:
            confidence = float(pred.get("confidence", 0.0))

            # Discard low-confidence detections
            if confidence < CONFIDENCE_THRESHOLD:
                continue

            results.append({
                "label":      str(pred.get("class", "Smoking")),
                "confidence": round(confidence, 3),
                "x":          int(pred.get("x", 0)),
                "y":          int(pred.get("y", 0)),
                "width":      int(pred.get("width", 0)),
                "height":     int(pred.get("height", 0)),
            })

        except (TypeError, ValueError) as exc:
            # Malformed individual prediction — skip it, log it, continue
            logger.warning(f"[smoking_detector] Skipping malformed prediction: {exc}")
            continue

    return results


# =============================================================================
# PUBLIC API
# =============================================================================

def detect(frame):
    print("=" * 60)
    print("detect() called")

    try:
        print("Frame valid:", frame is not None)

        raw = _run_inference(frame)

        print("Raw result:", raw)

        if raw is None:
            print("raw is None")
            return []

        parsed = _parse_detections(raw)

        print("Parsed:", parsed)

        return parsed

    except Exception as e:
        print("EXCEPTION:", e)
        import traceback
        traceback.print_exc()
        return []