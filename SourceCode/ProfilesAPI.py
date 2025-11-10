# ProfilesAPI.py
"""

This file defines the public interface for the profile service used by the
frontend. All functions currently raise NotImplementedError.

Expected data shape for a profile (example):
{
  "id": "<uid>",                 # Firestore doc id (same as uid)
  "uid": "<uid>",                # owner user id
  "displayName": "Alex",
  "bio": "Football enjoyer.",
  "homeCity": "Austin, TX",
  "favTeams": ["USA", "France"],
  "visibility": "Public",        # or "Private"
  "avatarUrl": "https://…/avatar.png",
  "created_at": "ISO8601 string",
  "updated_at": "ISO8601 string",
}
"""
from __future__ import annotations
import mimetypes
from datetime import datetime, timezone
from firebase_admin import firestore, storage
from HelperFunctions import initFirebase
from typing import Dict, Any, Optional, List, Literal, TypedDict

_db = None

class Profile(TypedDict, total=False):
    id: str
    uid: str
    displayName: str
    bio: str
    homeCity: str
    favTeams: List[str]
    visibility: Literal["Public", "Private"]
    avatarUrl: str
    created_at: str
    updated_at: str


def ensure_default_profile(uid: str, user_info: Dict[str, Any]) -> Profile:
    """
    Ensure a profile document exists for `uid`. If not, create a default
    document using `user_info` (e.g., displayName or email prefix) and return it.
    If it exists, return the existing document.

    Backend responsibilities:
      - Read Firestore doc at profiles/{uid}
      - If missing, create default with timestamps
      - Return the stored document as a dict (including "id")
    """
    db = _get_db()
    doc_ref = db.collection('profiles').document(uid)
    doc = doc_ref.get()
    
    if doc.exists:
        return _normalize_profile(doc)
    
    # Create default profile
    now = _now_iso()
    default_profile = {
        "uid": uid,
        "displayName": user_info.get("displayName") or user_info.get("email", "User"),
        "bio": "",
        "homeCity": "",
        "favTeams": [],
        "visibility": "Public",
        "avatarUrl": "",
        "created_at": now,
        "updated_at": now
    }
    
    doc_ref.set(default_profile)
    return {**default_profile, "id": uid}


def get_profile(uid: str) -> Profile:
    """
    Fetch and return the profile for `uid`. Return an empty dict if not found.

    Backend responsibilities:
      - Read Firestore doc at profiles/{uid}
      - Return {} if it does not exist
    """
    db = _get_db()
    doc = db.collection('profiles').document(uid).get()
    
    if not doc.exists:
        return {}
    
    return _normalize_profile(doc)


def save_profile(uid: str, updates: Dict[str, Any]) -> Profile:
    """
    Upsert profile fields for `uid` and return the updated document.

    Backend responsibilities:
      - Validate field types/lengths/allowed values
      - Set/refresh `updated_at` (and `created_at` on first write)
      - Merge fields into profiles/{uid}
      - Return the stored document as a dict (including "id")
    """
    db = _get_db()
    doc_ref = db.collection('profiles').document(uid)
    
    # Validate fields
    valid_updates = {
        k: v for k, v in updates.items() 
        if k in Profile.__annotations__ and k not in ['id', 'uid', 'created_at']
    }
    
    # Add timestamp
    valid_updates['updated_at'] = _now_iso()
    
    # Merge updates
    doc_ref.set(valid_updates, merge=True)
    
    # Return full updated doc
    return _normalize_profile(doc_ref.get())


def upload_avatar(uid: str, file_bytes: bytes, mime: str) -> Optional[str]:
    """
    Upload the avatar image for `uid` and return a public (or signed) URL.

    Backend responsibilities:
      - Validate MIME (image/png, image/jpeg), enforce size limits
      - Store to Firebase Storage (e.g., avatars/{uid}/avatar.png)
      - Make public or generate a signed URL
      - Return the URL string (or None on failure)
    """
    if mime not in ['image/jpeg', 'image/png']:
        return None
        
    try:
        bucket = storage.bucket()  # Get default bucket
        ext = mimetypes.guess_extension(mime) or '.png'
        blob = bucket.blob(f'avatars/{uid}/avatar{ext}')
        
        # Upload bytes
        blob.upload_from_string(
            file_bytes,
            content_type=mime
        )
        
        # Make public and return URL
        blob.make_public()
        return blob.public_url
        
    except Exception as e:
        print(f"Avatar upload failed: {e}")
        return None

def _get_db():
    """Return a lazily-initialized Firestore client.

    Uses `initFirebase()` once and caches the resulting client in a module-level
    variable to avoid redundant initializations when called repeatedly.
    """
    global _db
    if _db is None:
        _db = initFirebase()
    return _db

def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()

def _normalize_profile(doc) -> Profile:
    """Convert Firestore DocumentSnapshot to Profile dict."""
    data = doc.to_dict() or {}
    data['id'] = doc.id
    return data
