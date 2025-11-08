"""Firebase auth + Firestore helpers for Streamlit.
Provides REST wrappers (sign in/up, reset, verify, delete) and session_state
updates plus a lazy Firestore client via get_db()."""

import json
import os
import requests
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from HelperFunctions import initFirebase

_db = None

def get_db():
    """Return a lazily-initialized Firestore client.

    Uses `initFirebase()` once and caches the resulting client in a module-level
    variable to avoid redundant initializations when called repeatedly.
    """
    global _db
    if _db is None:
        _db = initFirebase()
    return _db

#This code is from a project Carlos wrote a while a go for a research project and provides a starting point for the team to work off

## TODO: ADD USE STREAMLIT KEYS IF NOT RUNNING LOCALLY 
# Firestore usage example (call get_db() where needed):
# db = get_db()

## -------------------------------------------------------------------------------------------------
## Firebase Auth API -------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def _get_firebase_web_api_key() -> str:
    """Resolve Firebase Web API key from config sources.

    Order of resolution:
        1) Streamlit secrets: [firebase].apiKey
        2) Env vars: FIREBASE_WEB_API_KEY or FIREBASE_API_KEY

    Raises:
        RuntimeError if no key is found.
    """
    # New preferred structure: [firebase] apiKey = "..."
    try:
        if "firebase" in st.secrets and "apiKey" in st.secrets["firebase"]:
            key = st.secrets["firebase"]["apiKey"]
            if key:
                return key
    except Exception:
        # st.secrets may not be available outside Streamlit runtime
        pass

    # Environment variable fallbacks
    key = os.getenv("FIREBASE_WEB_API_KEY") or os.getenv("FIREBASE_API_KEY")
    if key:
        return key

    raise RuntimeError(
        "Firebase Web API key not found. Set [firebase].apiKey in Streamlit secrets or FIREBASE_WEB_API_KEY env var."
    )

def sign_in_with_email_and_password(email, password):
    """Sign in a user using email/password via Firebase REST API.

    Args:
        email: User email address.
        password: User password.

    Returns:
        Parsed JSON response containing idToken and user details on success.

    Raises:
        requests.exceptions.HTTPError: For HTTP-level or Firebase auth errors.
    """
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def get_account_info(id_token):
    """Retrieve user account info given an ID token.

    Args:
        id_token: Firebase ID token for the user.

    Returns:
        Parsed JSON with user info list (users[0]).
    """
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_email_verification(id_token):
    """Send a verification email to the user corresponding to the ID token."""
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_password_reset_email(email):
    """Initiate a password reset email for the given address."""
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def create_user_with_email_and_password(email, password, first_name=None):
    """Create a new Firebase user with email/password.

    Optionally sets the Firebase displayName via `first_name`.
    Returns the parsed JSON response on success.
    """
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = {"email": email, "password": password, "returnSecureToken": True}
    if first_name:
        data["displayName"] = first_name
    request_object = requests.post(request_ref, headers=headers, data=json.dumps(data))
    raise_detailed_error(request_object)
    return request_object.json()

def delete_user_account(id_token):
    """Delete the Firebase account associated with the provided ID token."""
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/deleteAccount?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def raise_detailed_error(request_object):
    """Raise HTTPError with original response text included for context."""
    try:
        request_object.raise_for_status()
    except requests.exceptions.HTTPError as error:
        raise requests.exceptions.HTTPError(error, request_object.text)

## -------------------------------------------------------------------------------------------------
## Authentication functions ------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def sign_in(email:str, password:str) -> None:
    """High-level sign-in flow updating Streamlit session_state.

    On success, stores user_info and session_id, fetches chat history stub, and
    triggers a rerun for UI update. Sets `auth_warning` on common error cases.
    """
    try:
        # Attempt to sign in with email and password
        id_token = sign_in_with_email_and_password(email,password)['idToken']

        # Get account information
        user_info = get_account_info(id_token)["users"][0]
        st.session_state.session_id = user_info['localId']
        st.session_state.user_info = user_info

        # Load chat history and reset display flag
        st.session_state.chat_history = get_user_chat_history(user_info['localId'])
        st.session_state._chat_history_displayed = False

        st.rerun()

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"INVALID_EMAIL","EMAIL_NOT_FOUND","INVALID_PASSWORD","MISSING_PASSWORD"}:
            st.session_state.auth_warning = error_message
        else:
            st.session_state.auth_warning = 'Error: Please try again later'

    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Error: Please try again later'


def get_user_chat_history(user_id: str):
    """Retrieve chat history for a user (stub implementation).

    Replace with a Firestore-backed implementation using `get_db()` when
    ready. See commented example below for an outline.
    """
    return []


def create_account(email: str, password: str, first_name: str) -> None:
    """High-level account creation flow and session initialization.

    Sends verification email after creating the user. On success, populates
    session_state with `user_info` and marks `auth_success` for the UI.
    """
    try:
        result = create_user_with_email_and_password(email, password, first_name)
        id_token = result['idToken']
        send_email_verification(id_token)
        st.session_state.auth_success = 'Check your inbox to verify your email'

        user_info = get_account_info(id_token)["users"][0]
        st.session_state.session_id = user_info['localId']
        st.session_state.user_info = user_info  # Directly set user as authenticated
        st.session_state.auth_success = True

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message == "EMAIL_EXISTS":
            st.session_state.auth_warning = 'Error: Email belongs to existing account'
        elif error_message in {"INVALID_EMAIL","INVALID_PASSWORD","MISSING_PASSWORD","MISSING_EMAIL","WEAK_PASSWORD"}:
            st.session_state.auth_warning = error_message
        else:
            st.session_state.auth_warning = error_message
    except Exception as error:
        st.session_state.auth_warning = error

def reset_password(email:str) -> None:
    """Trigger a password reset email for the provided address.

    Sets `auth_success` or `auth_warning` in session_state for UI feedback.
    """
    try:
        send_password_reset_email(email)
        st.session_state.auth_success = 'Password reset link sent to your email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"MISSING_EMAIL","INVALID_EMAIL","EMAIL_NOT_FOUND"}:
            st.session_state.auth_warning = 'Error: Use a valid email'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'    
    
    except Exception:
        st.session_state.auth_warning = 'Error: Please try again later'




def sign_out() -> None:
    """Clear Streamlit session_state to sign the user out."""
    st.session_state.clear()
    st.session_state.auth_success = 'You have successfully signed out'


def delete_account(password:str) -> None:
    """Delete the currently signed-in user's account after re-authentication.

    Requires the user's password to obtain a fresh ID token before deletion.
    Clears session_state on success.
    """
    try:
        # Confirm email and password by signing in (and save id_token)
        id_token = sign_in_with_email_and_password(st.session_state.user_info['email'],password)['idToken']
        
        # Attempt to delete account
        delete_user_account(id_token)
        st.session_state.clear()
        st.session_state.auth_success = 'You have successfully deleted your account'

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        print(error_message)

    except Exception as error:
        print(error)

