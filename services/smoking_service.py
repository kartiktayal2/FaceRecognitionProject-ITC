"""
============================================================
services/smoking_service.py

Purpose
-------
Determine which smoking-related objects belong to a matched
Roboflow Person detection.

This module knows NOTHING about:

- Flask
- PostgreSQL
- Face Recognition
- Customers
- Dashboard

Input
-----
Matched Person Detection
+
All Roboflow Detections

Output
------
{
    "smoke": bool,
    "cigarette": bool,
    "vape": bool,
}

============================================================
"""

from typing import Dict, List


# ============================================================
# INTERNAL
# ============================================================

def _object_inside_person(person: Dict, obj: Dict) -> bool:
    """
    Returns True if the CENTER of the object lies inside
    the PERSON bounding box.
    """

    person_left = person["x"] - person["width"] / 2
    person_right = person["x"] + person["width"] / 2

    person_top = person["y"] - person["height"] / 2
    person_bottom = person["y"] + person["height"] / 2

    object_x = obj["x"]
    object_y = obj["y"]

    return (
        person_left <= object_x <= person_right
        and
        person_top <= object_y <= person_bottom
    )


# ============================================================
# PUBLIC API
# ============================================================

def analyse_person(person_detection: Dict,
                   detections: List[Dict]) -> Dict:
    """
    Analyse one matched person.

    Returns

    {
        "smoke": bool,
        "cigarette": bool,
        "vape": bool
    }
    """

    result = {
        "smoke": False,
        "cigarette": False,
        "vape": False,
    }

    if person_detection is None:
        return result

    for det in detections:

        label = det["label"].lower()

        if label == "person":
            continue

        if not _object_inside_person(person_detection, det):
            continue

        if label == "smoke":
            result["smoke"] = True

        elif label == "cigarette":
            result["cigarette"] = True

        elif label == "vape":
            result["vape"] = True

    return result