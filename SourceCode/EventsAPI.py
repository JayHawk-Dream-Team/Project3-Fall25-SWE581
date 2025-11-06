from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import uuid
from HelperFunctions import initFirebase

# Firestore client type is dynamic; keep local reference
# Use ISO 8601 UTC strings for timestamps (example: "2025-11-06T14:30:00Z")
def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string with 'Z' suffix."""
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

class EventNotFound(Exception):
    """Raised when an event document is not found."""
    pass

class PermissionDenied(Exception):
    """Raised when a user attempts an action they're not authorized for."""
    pass

def _get_collection(db):
    """Return the Firestore collection reference for events."""
    return db.collection("events")

def _normalize_event_for_return(doc) -> Dict[str, Any]:
    """
    Convert a Firestore DocumentSnapshot to a plain dictionary with the id included.
    This helps callers get the event data and its Firestore-generated id in one object.
    """
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data

def create_event(db,
                 event_data: Dict[str, Any],
                 user_id: str,
                 event_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new event document.

    Args:
        db: Firestore client (from initFirebase()).
        event_data: Partial or full event fields (title, description, location,
                    start_time (ISO), end_time (ISO), categories (list), published (bool)).
        user_id: UID of the creator (stored as created_by).
        event_id: Optional custom document ID. If None Firestore will generate one.

    Returns:
        The created event document as a dict including "id".

    Notes:
        - created_at and updated_at are added automatically as ISO strings.
        - published will default to False if not provided.
    """
    col = _get_collection(db)

    # Prepare canonical event object
    now = _now_iso()
    doc = {
        "title": event_data.get("title", ""),
        "description": event_data.get("description", ""),
        "location": event_data.get("location", ""),
        "start_time": event_data.get("start_time"),  # expected ISO string or None
        "end_time": event_data.get("end_time"),
        "created_by": user_id,
        "published": bool(event_data.get("published", False)),
        "created_at": now,
        "updated_at": now,
        "categories": event_data.get("categories", []) or []
    }

    # If user provided an event_id use it, else auto-id
    if event_id:
        doc_ref = col.document(event_id)
        doc_ref.set(doc)
        doc_snapshot = doc_ref.get()
    else:
        doc_ref = col.document()
        doc_ref.set(doc)
        doc_snapshot = doc_ref.get()

    return _normalize_event_for_return(doc_snapshot)

def get_event(db, event_id: str) -> Dict[str, Any]:
    """
    Retrieve a single event by its Firestore document ID.

    Raises:
        EventNotFound if the event doesn't exist.
    """
    col = _get_collection(db)
    doc_ref = col.document(event_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise EventNotFound(f"Event with id '{event_id}' not found.")
    return _normalize_event_for_return(doc)

def list_events(db, published: Optional[bool] = None, limit: Optional[int] = None, start_after: Optional[str] = None
                ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List events with optional filters.

    Args:
        db: Firestore client
        published: If True return only published events; if False only unpublished;
                   if None return all.
        limit: maximum number of items to return (for pagination).
        start_after: event_id to start after (for simple pagination). This function
                     will use the 'created_at' ordering with start_after semantics.

    Returns:
        (events_list, next_start_after_id)
        - events_list: list of event dicts
        - next_start_after_id: ID to pass as start_after to fetch the next page, or None
    """
    col = _get_collection(db)
    query = col.order_by("created_at", direction="DESC")

    if published is True:
        query = query.where("published", "==", True)
    elif published is False:
        query = query.where("published", "==", False)

    docs = None
    if start_after:
        start_doc = col.document(start_after).get()
        if start_doc.exists:
            docs = query.start_after(start_doc).limit(limit or 50).stream()
        else:
            # start_after not found -> start from beginning
            docs = query.limit(limit or 50).stream()
    else:
        docs = query.limit(limit or 50).stream()

    results = [ _normalize_event_for_return(d) for d in docs ]

    # Determine next_start_after id for pagination (last doc id)
    next_id = results[-1]["id"] if results else None
    return results, next_id

def _ensure_exists_and_owner(db, event_id: str, user_id: str):
    """
    Helper to check an event exists and was created by user_id.

    Raises:
        EventNotFound
        PermissionDenied
    Returns:
        The DocumentReference for the event (useful for updates/deletes).
    """
    col = _get_collection(db)
    doc_ref = col.document(event_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise EventNotFound(f"Event with id '{event_id}' not found.")
    data = doc.to_dict() or {}
    if data.get("created_by") != user_id:
        raise PermissionDenied("Only the event creator can modify or delete this event.")
    return doc_ref

def update_event(db, event_id: str, updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Update fields on an event. Only the creator may update.

    Args:
        db: Firestore client
        event_id: document id to update
        updates: fields to update (e.g., {"title": "New title", "location": "New loc"})
        user_id: UID of the user attempting the update

    Returns:
        The updated event dict.

    Notes:
        - start_time, end_time expected as ISO strings if provided.
        - created_by cannot be changed via updates.
    """
    # Confirm existence and permission
    doc_ref = _ensure_exists_and_owner(db, event_id, user_id)

    # Prevent changing ownership or created_at accidentally
    updates = dict(updates)  # copy
    updates.pop("created_by", None)
    updates.pop("created_at", None)

    # Touch updated_at
    updates["updated_at"] = _now_iso()

    # Perform update
    doc_ref.update(updates)
    doc = doc_ref.get()
    return _normalize_event_for_return(doc)

def publish_event(db, event_id: str, user_id: str) -> Dict[str, Any]:
    """
    Set published=True on the event. Only creator allowed.
    """
    doc_ref = _ensure_exists_and_owner(db, event_id, user_id)
    updates = {"published": True, "updated_at": _now_iso()}
    doc_ref.update(updates)
    return _normalize_event_for_return(doc_ref.get())

def unpublish_event(db, event_id: str, user_id: str) -> Dict[str, Any]:
    """
    Set published=False on the event. Only creator allowed.
    """
    doc_ref = _ensure_exists_and_owner(db, event_id, user_id)
    updates = {"published": False, "updated_at": _now_iso()}
    doc_ref.update(updates)
    return _normalize_event_for_return(doc_ref.get())

def delete_event(db, event_id: str, user_id: str) -> None:
    """
    Delete an event document. Only the creator may delete.

    Returns:
        None

    Raises:
        EventNotFound, PermissionDenied
    """
    doc_ref = _ensure_exists_and_owner(db, event_id, user_id)
    doc_ref.delete()
    return None

def default_db():
    """
    Convenience helper to lazily initialize Firebase if caller doesn't
    want to pass `db` explicitly. Use `initFirebase()` from HelperFunctions.
    """
    return initFirebase()

if __name__ == "__main__":
    db = default_db()
    print("EventsAPI module loaded. Example list (published only):")
    events, next_id = list_events(db, published=True, limit=5)
    print("Found", len(events), "events. Next id:", next_id)
