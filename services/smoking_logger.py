"""
services/smoking_logger.py

Single responsibility:
Insert one smoking-related event into PostgreSQL.

This module NEVER performs detection.
It NEVER performs face recognition.
It ONLY writes one row into smoking_events.
"""

from database import get_connection


def log_smoking_event(
    customer_type: str,
    customer_id: int,
    event_type: str,
    confidence: float,
):
    """
    Insert a smoking event.

    customer_type:
        known
        unknown

    event_type:
        cigarette
        smoke
        vape
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO smoking_events
        (
            customer_type,
            customer_id,
            event_type,
            confidence
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            customer_type,
            customer_id,
            event_type,
            confidence,
        ),
    )

    conn.commit()

    cur.close()
    conn.close()