import streamlit as st
import requests
from AuthFunctions import sign_in, create_account, reset_password, sign_out
from HelperFunctions import initFirebase
import json
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import time

@st.cache_resource(show_spinner=False)
def get_db():
    """Cached Firestore client for UI usage when needed."""
    return initFirebase()

##Basic User Interface is based on another project Carlos wrote and is merely to be a starting point as a reference 

# Initialize session state for authentication
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

if 'show_signup' not in st.session_state:
    st.session_state.show_signup = True  # Force Sign Up as default


# Initialize session state for chat display
if 'show_reset' not in st.session_state:
    st.session_state.show_reset = False
# Initialize session state
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'auth_warning' not in st.session_state:
    st.session_state.auth_warning = None
if 'auth_success' not in st.session_state:
    st.session_state.auth_success = None
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session_id' not in st.session_state:
    if st.session_state.get('user_info'):
        st.session_state.session_id = st.session_state.user_info['localId']  # Firebase UID
    else:
        st.session_state.session_id = "guest_user"



def show_auth_pages():
    st.title("HomeStand")

    # Create tab-like buttons
    col1, col2, col3 = st.columns(3)
    with col2:
        signup_btn = st.button("Sign In",
                              type="primary" if not st.session_state.show_signup and not st.session_state.show_reset else "secondary")
    with col1:
        signin_btn = st.button("Create Account",
                              type="primary" if st.session_state.show_signup and not st.session_state.show_reset else "secondary")
    with col3:
        reset_btn = st.button("Reset Password",
                             type="primary" if st.session_state.show_reset else "secondary")

    # Handle button clicks
    if signup_btn:
        st.session_state.show_signup = False
        st.session_state.show_reset = False
        st.rerun()

    if signin_btn:
        st.session_state.show_signup = True
        st.session_state.show_reset = False
        st.rerun()

    if reset_btn:
        st.session_state.show_signup = False
        st.session_state.show_reset = True
        st.rerun()

    # Show the appropriate form
    if st.session_state.show_reset:
        show_password_reset_form()
    elif st.session_state.show_signup:
        show_signup_form()
    else:
        show_signin_form()

def show_signup_form():

    with st.form("signup_form"):
        st.subheader("Create Your Account")
        first_name = st.text_input("First Name", key="signup_name")
        email = st.text_input("Email Address", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")

        if st.form_submit_button("Join Now", type="primary"):
            if not all([first_name, email, password]):
                st.error("Please fill all fields")
            else:
                create_account(email, password, first_name)
                if st.session_state.get('auth_success'):
                    st.rerun()  # Go straight to chat

    if st.session_state.get('auth_warning'):
        st.warning(st.session_state.auth_warning)

    st.caption("Already have an account? Click 'Sign In' above")

def show_signin_form():
    with st.form("signin_form"):
        st.subheader("Sign In to Your Account")
        email = st.text_input("Email Address", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_pass")

        if st.form_submit_button("Continue", type="primary"):
            sign_in(email, password)

    if st.session_state.get('auth_warning'):
        st.warning(st.session_state.auth_warning)

    st.caption("Need an account? Click 'Create Account' above")

def show_password_reset_form():
    with st.form("password_reset_form"):
        st.subheader("Reset Your Password")
        email = st.text_input("Email Address", key="reset_email")

        if st.form_submit_button("Send Reset Link", type="primary"):
            reset_password(email)

    if st.session_state.get('auth_warning'):
        st.warning(st.session_state.auth_warning)
    if st.session_state.get('auth_success'):
        st.success(st.session_state.auth_success)

    st.caption("Remember your password? Click 'Sign In' above")


def show_logged_in_view():
    """Simple placeholder view shown after successful login."""
    user = st.session_state.get('user_info') or {}
    name = user.get('displayName') or user.get('email') or 'User'

    st.title("You're in")
    st.success(f"Signed in as {name}")
    st.caption("This is a placeholder view after successful authentication. Replace with your app dashboard.")

    with st.expander("Session details", expanded=False):
        st.json({k: v for k, v in user.items() if k in ("email", "localId", "emailVerified", "displayName")})

    col1, col2 = st.columns(2)
    if col1.button("Sign out"):
        sign_out()
        st.rerun()

if st.session_state.get("user_info"):
    show_logged_in_view()
else:
    show_auth_pages()
