import json
import os
import requests
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from HelperFunctions import initFirebase

_db = None

def get_db():
    """Lazy-initialize and return a Firestore client via initFirebase()."""
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
    """Resolve the Firebase Web API key from Streamlit secrets or env vars.

    Supports both the new [firebase] block (apiKey) and legacy FIREBASE_WEB_API_KEY.
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
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def get_account_info(id_token):
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_email_verification(id_token):
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_password_reset_email(email):
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def create_user_with_email_and_password(email, password, first_name=None):
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
    api_key = _get_firebase_web_api_key()
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/deleteAccount?key={0}".format(api_key)
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def raise_detailed_error(request_object):
    try:
        request_object.raise_for_status()
    except requests.exceptions.HTTPError as error:
        raise requests.exceptions.HTTPError(error, request_object.text)

## -------------------------------------------------------------------------------------------------
## Authentication functions ------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def sign_in(email:str, password:str) -> None:
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
    """TEMP stub. Replace with Firestore-backed history using get_db().

    Example when ready:
        db = get_db()
        docs = db.collection('chat_history').document(user_id).collection('messages').order_by('ts').stream()
        return [d.to_dict() for d in docs]
    """
    return []


def create_account(email: str, password: str, first_name: str) -> None:
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
    st.session_state.clear()
    st.session_state.auth_success = 'You have successfully signed out'


def delete_account(password:str) -> None:
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

