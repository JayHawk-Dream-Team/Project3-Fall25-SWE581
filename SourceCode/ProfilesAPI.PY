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
from typing import Dict, Any, Optional, List, Literal, TypedDict


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
    raise NotImplementedError("ensure_default_profile: backend not implemented")


def get_profile(uid: str) -> Profile:
    """
    Fetch and return the profile for `uid`. Return an empty dict if not found.

    Backend responsibilities:
      - Read Firestore doc at profiles/{uid}
      - Return {} if it does not exist
    """
    raise NotImplementedError("get_profile: backend not implemented")


def save_profile(uid: str, updates: Dict[str, Any]) -> Profile:
    """
    Upsert profile fields for `uid` and return the updated document.

    Backend responsibilities:
      - Validate field types/lengths/allowed values
      - Set/refresh `updated_at` (and `created_at` on first write)
      - Merge fields into profiles/{uid}
      - Return the stored document as a dict (including "id")
    """
    raise NotImplementedError("save_profile: backend not implemented")


def upload_avatar(uid: str, file_bytes: bytes, mime: str) -> Optional[str]:
    """
    Upload the avatar image for `uid` and return a public (or signed) URL.

    Backend responsibilities:
      - Validate MIME (image/png, image/jpeg), enforce size limits
      - Store to Firebase Storage (e.g., avatars/{uid}/avatar.png)
      - Make public or generate a signed URL
      - Return the URL string (or None on failure)
    """
    raise NotImplementedError("upload_avatar: backend not implemented")