import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(0, PROJECT_ROOT)

from services.smoking_service import analyse_person

person = {
    "label": "Person",
    "x": 300,
    "y": 300,
    "width": 300,
    "height": 400,
}

detections = [

    person,

    {
        "label": "Cigarette",
        "x": 320,
        "y": 250,
        "width": 20,
        "height": 20,
    },

    {
        "label": "Smoke",
        "x": 280,
        "y": 180,
        "width": 40,
        "height": 40,
    },

    {
        "label": "Vape",
        "x": 700,
        "y": 700,
        "width": 40,
        "height": 40,
    },
]

print(analyse_person(person, detections))