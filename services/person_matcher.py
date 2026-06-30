"""
============================================================
services/person_matcher.py

Purpose
-------
Match a face-recognition bounding box with a Roboflow PERSON
bounding box.

This module DOES NOT know anything about:

- Flask
- PostgreSQL
- Customers
- Unknown customers
- Dashboard

It only answers one question:

"Does this face belong to this detected person?"

============================================================
"""

from typing import List, Dict, Optional


def _center_of_face(face_box):
    """
    face_box = (top, right, bottom, left)

    Returns:
        (x, y)
    """

    top, right, bottom, left = face_box

    x = (left + right) / 2
    y = (top + bottom) / 2

    return x, y


def _inside_person(face_center, person):

    x, y = face_center

    left = person["x"] - person["width"] / 2
    right = person["x"] + person["width"] / 2

    top = person["y"] - person["height"] / 2
    bottom = person["y"] + person["height"] / 2

    return (
        left <= x <= right and
        top <= y <= bottom
    )


def match_face_to_person(face_box,
                         detections: List[Dict]) -> Optional[Dict]:
    """
    Match a face to the BEST Person detection.

    Strategy
    --------
    1. Ignore all non-person detections.
    2. Keep only person boxes that contain the face centre.
    3. If multiple person boxes contain the face,
       choose the smallest one (most precise).

    Returns
    -------
    Matching person dict or None.
    """

    face_center = _center_of_face(face_box)

    best_match = None
    best_area = float("inf")

    for det in detections:

        if det["label"].lower() != "person":
            continue

        if not _inside_person(face_center, det):
            continue

        area = det["width"] * det["height"]

        if area < best_area:
            best_area = area
            best_match = det

    return best_match