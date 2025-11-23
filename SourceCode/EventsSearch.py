"""Event search and dashboard rendering utilities.

single function show_events_dashboard() that the authentication layer can
invoke once a user is signed in.

Responsibilities:
  - Fetch and display events (with search/filter and pagination stub).
  - Provide event creation form using EventsAPI.create_event.

The caller (Auth_UserInterface) must ensure that `st.session_state.user_info`
is populated before calling `show_events_dashboard`.
"""

import streamlit as st
from EventsSearchAPI import list_filtered_events as list_events
from HelperFunctions import initFirebase
from RSVP_API import (
    create_rsvp,
    get_event_rsvp_count,
    check_user_rsvp,
    RSVPAlreadyExists,
    EventFull
)
from RSVP_UI import is_event_past

@st.cache_resource(show_spinner=False)
def _db():
	"""Return a cached Firestore client for event operations."""
	return initFirebase()

def initialize_search_session_state():
    """Initialize session state for search page."""
    if 'rsvp_success_msg' not in st.session_state:
        st.session_state.rsvp_success_msg = None
    if 'rsvp_error_msg' not in st.session_state:
        st.session_state.rsvp_error_msg = None


def get_seats_left(db, event: dict) -> int:
    """Calculate remaining seats for an event."""
    capacity = event.get('capacity', 0)
    if capacity == 0:
        return 0
    try:
        rsvp_count = get_event_rsvp_count(db, event.get('id'))
    except NotImplementedError:
        # Fallback: use rsvp_count from event if API not implemented
        rsvp_count = event.get('rsvp_count', 0)
    return max(0, capacity - rsvp_count)


def is_event_full(db, event: dict) -> bool:
    """Check if an event has reached capacity."""
    return get_seats_left(db, event) <= 0


def has_user_rsvped(db, event_id: str, user_id: str) -> bool:
    """Check if user has already RSVP'd to this event."""
    try:
        return check_user_rsvp(db, event_id, user_id)
    except NotImplementedError:
        # Fallback: assume not RSVP'd if API not implemented
        return False


def handle_rsvp(db, event_id: str, user_id: str, event_title: str):
    """Handle RSVP button click."""
    try:
        create_rsvp(db, event_id, user_id)
        st.session_state.rsvp_success_msg = f"Successfully RSVP'd to '{event_title}'!"
    except RSVPAlreadyExists:
        st.session_state.rsvp_error_msg = "You have already RSVP'd to this event."
    except EventFull:
        st.session_state.rsvp_error_msg = "Sorry, this event is full."
    except Exception as e:
        st.session_state.rsvp_error_msg = f"Error: {str(e)}"

def show_events_dashboard():
	"""Render the authenticated Events Home page with search, filter, and event list.

	Expects `st.session_state.user_info` to contain Firebase user data with
	'localId', 'email', and optionally 'displayName'.
	"""
	user = st.session_state.get("user_info") or {}
	name = user.get("displayName") or user.get("email", "User")
	uid = user.get("localId", "unknown_user")
	db = _db()

	# --- Header ---
	st.title("HomeStand Dashboard")
	st.caption(f"Signed in as **{name}**")

	# --- Search + Filter Row ---
	col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.5, 1])
	with col1:
		search_text = st.text_input("🔍 Search Events", placeholder="Search by title or description...")
	with col2:
		location_filter = st.text_input("📍 Location", placeholder="City or State...")
	with col3:
		date_filter = st.date_input("📅 Date (optional)", value=None)
	with col4:
		published_filter = st.selectbox("Filter", ["All", "Published", "Unpublished"])
	with col5:
		if st.button(label="🔄"):
			st.rerun()


	# Create Event UI removed per request.

	# --- Fetch Events ---
	filter_flag = None
	if published_filter == "Published":
		filter_flag = True
	elif published_filter == "Unpublished":
		filter_flag = False

	events, next_id = list_events(db,published=filter_flag,limit=25,search_text=search_text or None,location=location_filter or None, date=date_filter.isoformat() if date_filter else None)
	
	# --- Search Filtering (client-side) ---
	if search_text:
		lowered = search_text.lower()
		events = [
			e for e in events
			if lowered in e.get("title", "").lower() or lowered in e.get("description", "").lower()
		]

	# --- Display Events ---
	st.subheader("📅 Events")
	if not events:
		st.info("No events found. Try adjusting your filters or create a new event.")
	else:
		for e in events:
			event_id = e.get('id')
			capacity = e.get('capacity', 0)
			seats_left = get_seats_left(db, e)
			is_full = seats_left <= 0
			user_has_rsvped = has_user_rsvped(db, event_id, uid)
			is_own_event = e.get('created_by') == uid
			event_passed = is_event_past(e.get('start_time'))
		
			with st.container():
                # Event header with title
				col_title, col_status = st.columns([3, 1])
			with col_title:
				st.markdown(f"### {e['title']}")
			with col_status:
				if 0 < seats_left <= 5:
					st.markdown(f"🟡 **{seats_left} seats left**")

			# Description
			st.write(e.get("description", ""))

			# Event details row
			col_details, col_seats, col_rsvp = st.columns([2, 1, 1])

			with col_details:
				start_time = e.get('start_time', '').split('T')
				st.caption(f"📍 {e.get('location', 'Unknown')} | 🕒 {start_time[0]} | {start_time[1][:-1]}")

			with col_seats:
				# Dynamic seats display
				if capacity > 0:
					enrolled = capacity - seats_left
					st.caption(f"**Seats:** {enrolled}/{capacity}")
				else:
					st.caption("Seats: Unlimited")

			with col_rsvp:
				# RSVP Button logic
				if is_own_event:
					st.caption("*Your event*")
				elif user_has_rsvped:
					st.success("✅ Registered")
				elif is_full:
					st.error("*🔴 FULL*")
				elif event_passed:
					st.warning("Event has Passed")
				else:
					if st.button("🎫 RSVP", key=f"rsvp_{event_id}"):
						handle_rsvp(db, event_id, uid, e.get('title', 'Event'))
						st.rerun()
				
			st.divider()

	# --- Pagination Placeholder ---
	if next_id:
		st.button("Load More Events")



