"""Streamlit Authentication UI layer for HomeStand.

This module provides a tabbed user interface for account creation,
sign in, and password reset flows using Firebase Authentication via helper
functions defined in AuthFunctions. After successful authentication a simple
logged in placeholder view is shown which will be replaced with the real app
dashboard.
"""

import streamlit as st
import requests
from AuthFunctions import sign_in, create_account, reset_password, sign_out
from HelperFunctions import initFirebase
from EventsSearchAPI import list_filtered_events as list_events
import json
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import time
from EventsSearch import show_events_dashboard
from Events_UI import show_event_management_interface

@st.cache_resource(show_spinner=False)
def get_db():
    """Return a cached Firestore client.

    This is a thin wrapper around `initFirebase()` allowing UI components to
    access Firestore efficiently. Currently not heavily used but retained for
    future expansion (e.g., storing user preferences or chat transcripts).
    """
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
    """Render the authentication landing view with tab-like navigation.

    Displays buttons acting as tabs for Create Account, Sign In, and Reset
    Password flows. Based on session_state flags, the corresponding form is
    shown. Button clicks update flags and trigger a rerun to refresh UI.
    """
    st.title("HomeStand")

    # Create tab-like buttons
    col1, col2, col3 = st.columns(3)
    with col2:
        signup_btn = st.button("Sign In", key="sigin",
                              type="primary" if not st.session_state.show_signup and not st.session_state.show_reset else "secondary")
    with col1:
        signin_btn = st.button("Create Account", key="signup",
                              type="primary" if st.session_state.show_signup and not st.session_state.show_reset else "secondary")
    with col3:
        reset_btn = st.button("Reset Password", key="resetpwd",
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
    """Display the account creation form.

    Collects first name (mapped to Firebase displayName), email, and password.
    On submit validates completeness before delegating to `create_account`.
    Successful creation triggers a rerun (which will transition to post-login
    view) while warnings are surfaced via session_state.
    """

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
    """Display the sign-in form.

    Accepts email and password then calls `sign_in` which handles Firebase
    authentication, session population, chat history load, and rerun. Any
    auth warnings are shown below the form.
    """
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
    """Display the password reset request form.

    Takes an email address and invokes `reset_password` which triggers Firebase
    to send a reset link. Success and warning messages are surfaced below.
    """
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
    """Render sidebar navigation and delegate to selected logged-in view.
    """

    st.sidebar.markdown("# Navigation")

    page = st.sidebar.radio(
        "", ["Events Dashboard", "Event Management"], label_visibility="visible"
    )

    if page == "Events Dashboard":
        show_events_dashboard()
    elif page == "Event Management":
        show_event_management_interface()
    
    st.sidebar.divider()
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        sign_out()
        st.rerun()


if st.session_state.get("user_info"):
    show_logged_in_view()
else:
    show_auth_pages()
