import os
import sys

# ----------------------------------------------------------
# Allow experiments/ to import project modules.
# ----------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(0, PROJECT_ROOT)

from services.person_matcher import match_face_to_person


face = (
    100,
    200,
    200,
    100
)

detections = [

    {
        "label": "Person",
        "x": 150,
        "y": 150,
        "width": 350,
        "height": 350
    },

    {
        "label": "Person",
        "x": 150,
        "y": 150,
        "width": 180,
        "height": 180
    }

]

print(match_face_to_person(face, detections))