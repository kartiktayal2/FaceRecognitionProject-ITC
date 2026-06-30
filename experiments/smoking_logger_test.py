import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from services.smoking_logger import log_smoking_event

log_smoking_event(
    customer_type="known",
    customer_id=1,
    event_type="cigarette",
    confidence=0.98,
)

print("Smoke event inserted successfully.")