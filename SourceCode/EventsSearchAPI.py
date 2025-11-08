# EventsSearchAPI.py
"""
Provides enhanced search and filter capabilities for events,
wrapping the base EventsAPI.list_events() function.

Supports:
 - published filter (handled by EventsAPI)
 - client-side search (title, description)
 - location filter (city/state substring match)
 - date filter (events starting on a specific date)
"""

from typing import Optional, Tuple, List, Dict, Any
from EventsAPI import list_events as base_list


def list_filtered_events(
    db,
    published: Optional[bool] = None,
    limit: Optional[int] = None,
    start_after: Optional[str] = None,
    search_text: Optional[str] = None,
    location: Optional[str] = None,
    date: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Combine Firestore event listing with local text/date/location filtering.
    """

    # 1️⃣ Get base list from Firestore (uses published flag)
    events, next_id = base_list(db, published=published, limit=limit, start_after=start_after)

    # 2️⃣ Apply optional client-side filters
    if search_text:
        lowered = search_text.lower()
        events = [
            e for e in events
            if lowered in e.get("title", "").lower() or lowered in e.get("description", "").lower()
        ]

    if location:
        lowered = location.lower()
        events = [
            e for e in events
            if lowered in e.get("location", "").lower()
        ]

    if date:
        # Match ISO 8601 prefix 'YYYY-MM-DD'
        events = [
            e for e in events
            if e.get("start_time", "").startswith(date)
        ]

    return events, next_id
