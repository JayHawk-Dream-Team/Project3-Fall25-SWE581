import streamlit as st
import requests
from AuthFunctions import sign_in, create_account, reset_password
import json
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import time

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate('firebaseKEYAFSTDUY.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

##Basic User Interface is based on another project Carlos wrote and is merely to be a starting point as a reference 

# Initialize session state for authentication
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

if 'show_signup' not in st.session_state:
    st.session_state.show_signup = True  # Force Sign Up as default


def show_auth_pages():
    st.title("Welcome to Our Super Cool App For Project 3")

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

if st.session_state.get("user_info"):
      #TODO: Replace this with our actual app once we write something really cool other wise this is place holder
      show_auth_pages()
else:
    show_auth_pages()
