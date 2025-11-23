"""RSVP UI components for HomeStand.

This module provides the UI for viewing and managing RSVPs.
Users can see their RSVP'd events and cancel them.
"""
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List
from HelperFunctions import initFirebase
# Import RSVP API functions (to be implemented by backend)
from RSVP_API import (
    get_user_rsvps,
    cancel_rsvp,
    RSVPNotFound,
    CancellationNotAllowed
)

@st.cache_resource(show_spinner=False)
def get_db():
    """Cached Firestore client."""
    return initFirebase()


def initialize_rsvp_session_state():
    """Initialize session state variables for RSVP management."""
    if 'rsvp_success_message' not in st.session_state:
        st.session_state.rsvp_success_message = None
    if 'rsvp_error_message' not in st.session_state:
        st.session_state.rsvp_error_message = None


def clear_rsvp_messages():
    """Clear success and error messages."""
    st.session_state.rsvp_success_message = None
    st.session_state.rsvp_error_message = None


def parse_iso_to_datetime(iso_string: str):
    """Parse ISO 8601 string to datetime object."""
    if not iso_string:
        return datetime.now()
    iso_clean = iso_string.rstrip('Z')
    return datetime.fromisoformat(iso_clean)


def is_event_past(start_time: str):
    """Check if an event's start time has already passed."""
    if not start_time:
        return False
    event_dt = parse_iso_to_datetime(start_time)
    return event_dt < datetime.now()


def show_rsvp_card(rsvp: Dict[str, Any], user_id: str, db):
    """
    Display a single RSVP card with event details and cancel option.
    rsvp: RSVP data dictionary (should include event details)
    """
    event = rsvp.get('event', {})
    event_id = rsvp.get('event_id') or event.get('id')
    rsvp_id = rsvp.get('id')
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {event.get('title', 'Untitled Event')}")
        
        with col2:
            # Check if event has passed
            event_passed = is_event_past(event.get('start_time'))
            if event_passed:
                st.markdown("⏰ **Past Event**")
        
        # Event details
        st.markdown(f"**📍 Location:** {event.get('location', 'TBA')}")
        
        # Parse and display times
        if event.get('start_time'):
            start_dt = parse_iso_to_datetime(event.get('start_time'))
            st.markdown(f"**Date:** {start_dt.strftime('%B %d, %Y')}")
            
            if event.get('end_time'):
                end_dt = parse_iso_to_datetime(event.get('end_time'))
                st.markdown(f"**Time:** {start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}")
            else:
                st.markdown(f"**Time:** {start_dt.strftime('%I:%M %p')}")
        
        # RSVP timestamp
        if rsvp.get('rsvp_at'):
            rsvp_dt = parse_iso_to_datetime(rsvp.get('rsvp_at'))
            st.caption(f"RSVP'd on: {rsvp_dt.strftime('%B %d, %Y at %I:%M %p')}")
        
        # Description expander
        if event.get('description'):
            with st.expander("Event Description"):
                st.write(event['description'])
        
        # Categories
        if event.get('categories'):
            st.markdown("**Categories:** " + ", ".join(event['categories']))
        
        # Cancel button (only if event hasn't passed)
        if not event_passed:
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("❌ Cancel RSVP", key=f"cancel_rsvp_{rsvp_id}", type="secondary"):
                    st.session_state[f"confirm_cancel_{rsvp_id}"] = True
            
            # Confirmation dialog
            if st.session_state.get(f"confirm_cancel_{rsvp_id}", False):
                st.warning(f"Are you sure you want to cancel your RSVP for '{event.get('title')}'?")
                col_yes, col_no = st.columns(2)
                
                with col_yes:
                    if st.button("Yes, cancel", type="primary", key=f"confirm_cancel_yes_{rsvp_id}"):
                        try:
                            cancel_rsvp(db, rsvp_id, user_id)
                            st.session_state.rsvp_success_message = f"RSVP for '{event.get('title')}' cancelled successfully"
                            st.session_state.pop(f"confirm_cancel_{rsvp_id}")
                            st.rerun()
                        except CancellationNotAllowed as e:
                            st.session_state.rsvp_error_message = str(e)
                            st.session_state.pop(f"confirm_cancel_{rsvp_id}")
                            st.rerun()
                with col_no:
                    if st.button("No, keep it", key=f"confirm_cancel_no_{rsvp_id}"):
                        st.session_state.pop(f"confirm_cancel_{rsvp_id}")
                        st.rerun()        
        st.divider()


def show_my_rsvps(db, user_id: str):
    """Display list of user's RSVPs."""
    st.markdown("<h2 style='text-align: center;'>My RSVPs</h2>", unsafe_allow_html=True)
    
    try:
        # Get all RSVPs for the user
        rsvps = get_user_rsvps(db, user_id)
        
        if not rsvps:
            st.info("You haven't RSVP'd to any events yet. Browse the Events Dashboard to find events!")
            return
        
        # Separate upcoming and past events
        upcoming_rsvps = []
        past_rsvps = []
        
        for rsvp in rsvps:
            event = rsvp.get('event', {})
            if is_event_past(event.get('start_time')):
                past_rsvps.append(rsvp)
            else:
                upcoming_rsvps.append(rsvp)
        
        # Display upcoming RSVPs
        if upcoming_rsvps:
            st.markdown("#### 🎫:green[Upcoming Events]")
            for rsvp in upcoming_rsvps:
                show_rsvp_card(rsvp, user_id, db)
        
        # Display past RSVPs
        if past_rsvps:
            st.markdown("#### 📜:red[Past Events]")
            for rsvp in past_rsvps:
                show_rsvp_card(rsvp, user_id, db)
                
    except Exception as e:
        st.error(f"Error loading RSVPs: {str(e)}")


def show_rsvp_tab():
    """Main interface for RSVP management tab."""
    initialize_rsvp_session_state()
    
    # Check if user is logged in
    if not st.session_state.get('user_info'):
        st.warning("Please sign in to view your RSVPs.")
        return
    
    user_id = st.session_state.user_info.get('localId')
    db = get_db()
    
    # Display success/error messages
    if st.session_state.rsvp_success_message:
        st.success(st.session_state.rsvp_success_message)
        st.session_state.rsvp_success_message = None
    
    if st.session_state.rsvp_error_message:
        st.error(st.session_state.rsvp_error_message)
        st.session_state.rsvp_error_message = None
    
    # Show user's RSVPs
    show_my_rsvps(db, user_id)