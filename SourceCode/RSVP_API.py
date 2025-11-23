from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from google.cloud.firestore import FieldFilter, transactional
# --------------------------------------------------------------------
# Custom Exceptions
# --------------------------------------------------------------------

class RSVPNotFound(Exception): pass
class RSVPAlreadyExists(Exception): pass
class EventFull(Exception): pass
class CancellationNotAllowed(Exception): pass
class EventNotFound(Exception): pass


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()


def _get_rsvp_collection(db):
    return db.collection("rsvps")


def _get_events_collection(db):
    return db.collection("events")


# --------------------------------------------------------------------
# Create RSVP
# --------------------------------------------------------------------

def create_rsvp(db, event_id: str, user_id: str) -> Dict[str, Any]:

    events_col = _get_events_collection(db)
    rsvp_col = _get_rsvp_collection(db)

    event_ref = events_col.document(event_id)
    event_doc = event_ref.get()

    # 1. Event exists?
    if not event_doc.exists:
        raise EventNotFound(f"Event '{event_id}' not found")

    event_data = event_doc.to_dict()
    capacity = event_data.get("capacity", 0)
    rsvp_count = event_data.get("rsvp_count", 0)

    # 2. Check for existing active RSVP for this event + user
    existing = (
        rsvp_col.where(filter=FieldFilter("user_id", "==", user_id))
                .where(filter=FieldFilter("event_id", "==", event_id))
                .where(filter=FieldFilter("status", "==", "active"))
                .limit(1)
                .get()
    )

    if len(existing) > 0:
        raise RSVPAlreadyExists("User already has an active RSVP for this event")

    # 3. Check event capacity
    if rsvp_count >= capacity:
        raise EventFull("This event has reached capacity")

    # 4 + 5. Create RSVP and increment rsvp_count ATOMICALLY
    @transactional
    def txn_op(transaction):

        # Re-read inside transaction
        event_snapshot = event_ref.get(transaction=transaction)
        if not event_snapshot.exists:
            raise EventNotFound(f"Event '{event_id}' disappeared during transaction")

        event_info = event_snapshot.to_dict()
        if event_info.get("rsvp_count", 0) >= event_info.get("capacity", 0):
            raise EventFull("This event has reached capacity")

        # Create RSVP document
        rsvp_ref = rsvp_col.document()
        rsvp_data = {
            "user_id": user_id,
            "event_id": event_id,
            "rsvp_at": _now_iso(),
            "status": "active"
        }

        transaction.set(rsvp_ref, rsvp_data)

        # Increment count
        transaction.update(event_ref, {
            "rsvp_count": event_info.get("rsvp_count", 0) + 1
        })

        return {**rsvp_data, "id": rsvp_ref.id, "event": event_data}

    transaction = db.transaction()
    return txn_op(transaction)


# --------------------------------------------------------------------
# Get User RSVPs
# --------------------------------------------------------------------

def get_user_rsvps(db, user_id: str) -> List[Dict[str, Any]]:

    rsvp_col = _get_rsvp_collection(db)
    event_col = _get_events_collection(db)

    # 1. Fetch active RSVPs for this user
    rsvps = rsvp_col.where(filter=FieldFilter("user_id", "==", user_id))\
                    .where(filter=FieldFilter("status", "==", "active"))\
                    .get()

    results = []

    for doc in rsvps:
        rsvp_data = doc.to_dict()
        rsvp_id = doc.id
        event_id = rsvp_data.get("event_id")

        # 2. Fetch event details
        event_doc = event_col.document(event_id).get()
        if not event_doc.exists:
            continue  # event deleted? skip

        event_data = event_doc.to_dict()

        results.append({
            **rsvp_data,
            "id": rsvp_id,
            "event": event_data
        })

    # 3. Sort by event start_time
    def sort_key(item):
        event = item.get("event", {})
        t = event.get("start_time")
        if not t:
            return datetime.max
        return datetime.fromisoformat(t.replace("Z", "+00:00"))

    return sorted(results, key=sort_key)


# --------------------------------------------------------------------
# Get Event RSVP Count
# --------------------------------------------------------------------

def get_event_rsvp_count(db, event_id: str) -> int:
    event_ref = _get_events_collection(db).document(event_id)
    event_doc = event_ref.get()
    if event_doc.exists:
        return event_doc.to_dict().get("rsvp_count", 0)
    return 0


# --------------------------------------------------------------------
# Check if user has RSVP
# --------------------------------------------------------------------

def check_user_rsvp(db, event_id: str, user_id: str) -> bool:

    rsvp_col = _get_rsvp_collection(db)
    existing = (
        rsvp_col.where(filter=FieldFilter("user_id", "==", user_id))
                .where(filter=FieldFilter("event_id", "==", event_id))
                .where(filter=FieldFilter("status", "==", "active"))
                .limit(1)
                .get()
    )
    return len(existing) > 0


# --------------------------------------------------------------------
# Cancel RSVP
# --------------------------------------------------------------------

def cancel_rsvp(db, rsvp_id: str, user_id: str) -> None:

    rsvp_col = _get_rsvp_collection(db)
    events_col = _get_events_collection(db)

    rsvp_ref = rsvp_col.document(rsvp_id)
    rsvp_doc = rsvp_ref.get()

    # 1. Exists?
    if not rsvp_doc.exists:
        raise RSVPNotFound("RSVP not found")

    rsvp_data = rsvp_doc.to_dict()

    # 2. User owns RSVP?
    if rsvp_data.get("user_id") != user_id:
        raise CancellationNotAllowed("User is not owner of this RSVP")

    event_id = rsvp_data.get("event_id")
    event_ref = events_col.document(event_id)
    event_doc = event_ref.get()

    if not event_doc.exists:
        raise EventNotFound("Event not found")

    event_data = event_doc.to_dict()

    # 3. Event hasn't passed
    start_time = event_data.get("start_time")
    if start_time:
        event_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if datetime.utcnow().replace(tzinfo=timezone.utc) > event_dt:
            raise CancellationNotAllowed("Cannot cancel RSVP after event start")

    # 4 + 5: Cancel RSVP + decrement count atomically
    @transactional
    def txn_op(transaction):
        # you need to read everything first, then do all the writes 
        # Re-read inside transaction
        snap = rsvp_ref.get(transaction=transaction)
        event_snap = event_ref.get(transaction=transaction)

        if not snap.exists:
            raise RSVPNotFound("RSVP disappeared during transaction")

        transaction.update(rsvp_ref, {"status": "cancelled"})

        # decrement rsvp_count
        if event_snap.exists:
            count = event_snap.to_dict().get("rsvp_count", 0)
            transaction.update(event_ref, {"rsvp_count": max(0, count - 1)})

    transaction = db.transaction()
    txn_op(transaction)

    return {
        "id": rsvp_id,
        "status": "cancelled",
        "event_id": event_id
    }


# --------------------------------------------------------------------
# Get RSVP by event/user
# --------------------------------------------------------------------

def get_rsvp_by_event_and_user(db, event_id: str, user_id: str) -> Optional[Dict[str, Any]]:

    rsvp_col = _get_rsvp_collection(db)

    docs = (
        rsvp_col.where(filter=FieldFilter("event_id", "==", event_id))
                .where(filter=FieldFilter("user_id", "==", user_id))
                .limit(1)
                .get()
    )

    if not docs:
        return None

    doc = docs[0]
    return {**doc.to_dict(), "id": doc.id}
