import requests
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# This function is from the ShowTracker App we made in the EECS348 Software Engineering 1 Project 

## TODO: IF YOU WANT TO RUN THIS LOCALLY. Change this Function. I have left another comment in it with instructions.
def initFirebase():
    try:
        # Fetch credentials from Streamlit's secrets
        firebase_credentials = {
            "type": st.secrets["type"],
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets["private_key_id"],
            "private_key": st.secrets["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets["client_id"],
            "auth_uri": st.secrets["auth_uri"],
            "token_uri": st.secrets["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["client_x509_cert_url"]
        }

        # Create a credential object with the fetched credentials
        ## TODO: IF YOU WANT TO RUN THIS LOCALLY CHANGE CRED TO THIS
        # cred = credentials.Certificate("StAuth.json") Put path to your key here. Then comment out the next line
        cred = credentials.Certificate(firebase_credentials)

        # Initialize the Firebase app with the created credentials
        firebase_admin.initialize_app(cred)
        print("Firebase Initialized Successfully")
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")