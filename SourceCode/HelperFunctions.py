import os
from pathlib import Path
import requests
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

"""
Firebase initialization utilities

Supports two modes automatically:
- Local development: use a service-account JSON file if present.
- Remote (e.g., Streamlit Cloud): read credentials from Streamlit secrets.

Also ensures we don't double-initialize firebase_admin.
"""


def _try_local_service_account() -> credentials.Certificate | None:
    """Look for a local service-account JSON and return a Certificate if found."""
    candidate_paths = [
        Path.cwd() / "firebase_key_sweproj3_fall25.json",
        Path(__file__).parent / "firebase_key_sweproj3_fall25.json",
        Path.cwd() / "SourceCode" / "firebase_key_sweproj3_fall25.json",
    ]
    for p in candidate_paths:
        if p.exists():
            return credentials.Certificate(str(p))
    return None


def _try_streamlit_secrets_service_account() -> credentials.Certificate | None:
    """Construct a Certificate from Streamlit secrets if present.

    Expected structures:
    - Preferred: st.secrets["firebase_service_account"] as a TOML table with standard
      service account fields (type, project_id, private_key, client_email, ...).
    - Legacy fallback: required keys at the top level of st.secrets.
    """
    try:
        # Preferred namespaced block
        if "firebase_service_account" in st.secrets:
            sa = dict(st.secrets["firebase_service_account"])  # make a real dict
            if "private_key" in sa and isinstance(sa["private_key"], str):
                sa["private_key"] = sa["private_key"].replace("\\n", "\n")
            return credentials.Certificate(sa)

        # Legacy/non-namespaced fallback (top-level keys)
        required = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_x509_cert_url",
        ]
        if all(k in st.secrets for k in required):
            sa = {k: st.secrets[k] for k in required}
            sa["private_key"] = sa["private_key"].replace("\\n", "\n")
            return credentials.Certificate(sa)
    except Exception as e:
        # Don't crash here; just signal failure to caller
        print(f"Streamlit secrets lookup for Firebase service account failed: {e}")
    return None


def initFirebase():
    """Initialize Firebase Admin SDK and return a Firestore client.

    Resolution order:
    1) Local service-account JSON file named 'firebase_key_sweproj3_fall25.json'.
    2) Streamlit secrets block [firebase_service_account] or equivalent top-level keys.
    3) Application Default Credentials (ADC), if available.
    """
    # Already initialized? Just return a client
    if firebase_admin._apps:
        return firestore.client()

    # 1) Local file
    cred = _try_local_service_account()
    if cred:
        firebase_admin.initialize_app(cred)
        return firestore.client()

    # 2) Streamlit secrets
    cred = _try_streamlit_secrets_service_account()
    if cred:
        firebase_admin.initialize_app(cred)
        return firestore.client()

    # 3) ADC as a last resort (requires env or metadata server)
    try:
        project_id = None
        # Try to read projectId from [firebase] section if present
        if "firebase" in st.secrets and "projectId" in st.secrets["firebase"]:
            project_id = st.secrets["firebase"]["projectId"]
        project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")

        cred = credentials.ApplicationDefault()
        if project_id:
            firebase_admin.initialize_app(cred, {"projectId": project_id})
        else:
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        raise RuntimeError(
            "Failed to initialize Firebase Admin. Provide a local service account JSON "
            "or set Streamlit secrets [firebase_service_account]."
        ) from e