"""Event search and dashboard rendering utilities.

single function show_events_dashboard() that the authentication layer can
invoke once a user is signed in.

Responsibilities:
  - Fetch and display events (with search/filter and pagination stub).
  - Provide event creation form using EventsAPI.create_event.

The caller (Auth_UserInterface) must ensure that `st.session_state.user_info`
is populated before calling `show_events_dashboard`.
"""

from datetime import datetime
import streamlit as st
from EventsSearchAPI import list_filtered_events as list_events
from HelperFunctions import initFirebase
@st.cache_resource(show_spinner=False)
def _db():
	"""Return a cached Firestore client for event operations."""
	return initFirebase()

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
			with st.container():
				st.markdown(f"### {e['title']}")
				st.write(e.get("description", ""))
				st.caption(f"📍 {e.get('location', 'Unknown')} | 🕒 {e.get('start_time', '')}")
				st.divider()

	# --- Pagination Placeholder ---
	if next_id:
		st.button("Load More Events")



