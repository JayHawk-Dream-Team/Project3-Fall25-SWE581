import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from LocAutoComplete import suggest_location
from EventsAPI import (
    create_event,
    update_event,
    publish_event,
    unpublish_event,
    delete_event,
    get_event,
    list_events,
    EventNotFound,
    PermissionDenied
)
from HelperFunctions import initFirebase

@st.cache_resource(show_spinner=False)
def get_db():
    """Cached Firestore client."""
    return initFirebase()

# World Cup specific categories
WORLD_CUP_CATEGORIES = [
    "Match Viewing Party",
    "Fan Meetup",
    "Pre-Game Celebration",
    "Post-Game Party",
    "Group Stage Event",
    "Knockout Stage Event",
    "Final Watch Party",
    "Team Support Event",
    "Sports Bar Gathering",
    "Home Viewing Party",
    "Public Screening",
    "Other"
]

def initialize_event_session_state():
    """Initialize session state variables for event management."""
    if 'editing_event_id' not in st.session_state:
        st.session_state.editing_event_id = None
    if 'event_success_message' not in st.session_state:
        st.session_state.event_success_message = None
    if 'event_error_message' not in st.session_state:
        st.session_state.event_error_message = None
    if 'show_my_events' not in st.session_state:
        st.session_state.show_my_events = False
    if 'active_tab' not in st.session_state:
        # 0 create event, 1 my event
        st.session_state.active_tab = 0

def clear_event_messages():
    """Clear success and error messages."""
    st.session_state.event_success_message = None
    st.session_state.event_error_message = None

def validate_event_data(title: str, start_date: datetime.date, start_time: datetime.time,
                       end_time: datetime.time) -> tuple[bool, Optional[str]]:
    """
    validate event form data.
    returns (is_valid, error_message)
    """
    if not title or title.strip() == "":
        return False, "Event title is required"
    
    if len(title.strip()) < 3:
        return False, "Event title must be at least 3 characters"
    
    # combine date and time
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(start_date, end_time)

    # check if end is after start
    if end_datetime <= start_datetime:
        return False, "Event end time must be after start time"
    
    # check if event is not too far in the past (allow 1 hour grace period)
    if start_datetime < datetime.now() - timedelta(hours=1):
        return False, "Event start time cannot be in the past"
    
    return True, None

def format_datetime_for_api(date: datetime.date, time: datetime.time) -> str:
    """Convert date and time to ISO 8601 format string."""
    dt = datetime.combine(date, time)
    return dt.isoformat() + "Z"

def parse_iso_to_datetime(iso_string: Optional[str]) -> tuple[datetime.date, datetime.time]:
    """Parse ISO 8601 string to date and time objects."""
    if not iso_string:
        now = datetime.now()
        return now.date(), now.time()
    
    # remove 'Z' suffix if present and parse
    iso_clean = iso_string.rstrip('Z')
    dt = datetime.fromisoformat(iso_clean)
    return dt.date(), dt.time()

def show_event_creation_form(db, user_id: str, edit_mode: bool = False, event_data: Optional[Dict[str, Any]] = None):
    """
    display the event creation/editing form.
    
    db: Firestore database client
    user_id: Current user's ID
    edit_mode: Whether this is editing an existing event
    event_data: Existing event data if in edit mode
    """
    
    form_title = "Edit Event" if edit_mode else "Create New World Cup Event"
    st.subheader(form_title)
    
    # pre-populate form if editing
    default_title = event_data.get('title', '') if event_data else ''
    default_description = event_data.get('description', '') if event_data else ''
    default_location = event_data.get('location', '') if event_data else ''
    default_capacity = event_data.get('capacity', 10) if event_data else 10
    
    # parse dates/times for editing
    if event_data and event_data.get('start_time'):
        default_start_date, default_start_time = parse_iso_to_datetime(event_data['start_time'])
        _, default_end_time = parse_iso_to_datetime(event_data.get('end_time'))
    else:
        default_start_date = datetime.now().date()
        default_start_time = datetime.strptime("18:00", "%H:%M").time()
        default_end_time = datetime.strptime("21:00", "%H:%M").time()
    
    default_categories = event_data.get('categories', []) if event_data else []
    default_published = event_data.get('published', False) if event_data else False
    
    # initialize location in session state if not present
    if 'selected_location' not in st.session_state or edit_mode:
        st.session_state.selected_location = default_location
    
    # location autocomplete
    st.markdown("##### Location *")
    location_query = st.text_input(
        "Type to search for a location",
        value=st.session_state.selected_location,
        placeholder="Type location name...",
        key="location_search",
        help="Please Press Enter to validate your location"
    )
    
    # autocomplete
    options = suggest_location(location_query)
    if options:
        labels = [opt for opt in options]
        selected_label = st.selectbox(
            "Select from suggestions",
            labels,
            key="location_select"
        )
        # update session state when user selects
        sel = next(opt for opt in options if opt == selected_label)
        st.session_state.selected_location = sel
        #print(sel)
    else:
        # use whatever they typed
        st.session_state.selected_location = location_query
    
    # show selected location
    if st.session_state.selected_location:
        st.success(f"📍You have Selected: {st.session_state.selected_location}")
    
    st.divider()
    
    with st.form(key=f"event_form_{'edit' if edit_mode else 'create'}", clear_on_submit=not edit_mode):
        # Title nd Description
        title = st.text_input(
            "Title *",
            value=default_title,
            placeholder="France vs Spain WorldCup Final Watch Party"
        )

        description = st.text_area(
            "Description *",
            value=default_description,
            placeholder="Describe your World Cup event. What can attendees expect?"
        )

        # capacity
        capacity = st.number_input("Capacity *", min_value=default_capacity, max_value=300, value=default_capacity)
        
        # Date and Time
        start_date = st.date_input("Date *", value=default_start_date)
        
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Start Time *", value=default_start_time)
        
        with col2:
            end_time = st.time_input("End Time *", value=default_end_time)

        # categories
        categories = st.multiselect(
            "Event Categories",
            options=WORLD_CUP_CATEGORIES,
            default=default_categories,
            help="Select one or more categories that describe your event"
        )
        
        # published status
        published = st.checkbox(
            "Publish event immediately",
            value=default_published,
            help="Published events are visible to all users. Unpublished events are drafts."
        )
        
        # form submission buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submit_button = st.form_submit_button(
                "Update Event" if edit_mode else "Create Event",
                type="primary"
            )
        
        with col2:
            if edit_mode:
                cancel_button = st.form_submit_button("Cancel")
            else:
                cancel_button = False
        
        # handle form submission
        if submit_button:
            # get location from session state
            location = st.session_state.selected_location

            # check event limit - 3 max
            if not edit_mode:
                all_events, _ = list_events(db, published=None, limit=100)
                user_events = [e for e in all_events if e.get('created_by') == user_id]
                if len(user_events) >= 3:
                    st.session_state.event_error_message = "You have reached the maximum limit of 3 events."
                    st.rerun()

            # validate form data
            is_valid, error_msg = validate_event_data(title, start_date, start_time, end_time)
            
            if not is_valid:
                st.session_state.event_error_message = error_msg
                st.rerun()
            
            if not location or location.strip() == "":
                st.session_state.event_error_message = "Location is required"
                st.rerun()
            
            if not description or description.strip() == "":
                st.session_state.event_error_message = "Description is required"
                st.rerun()
            
            # prepare event data
            event_payload = {
                "title": title.strip(),
                "description": description.strip(),
                "location": location.strip(),
                "capacity": capacity,
                "start_time": format_datetime_for_api(start_date, start_time),
                "end_time": format_datetime_for_api(start_date, end_time),  # Fixed: use same date
                "categories": categories,
                "published": published
            }
            
            try:
                if edit_mode and event_data:
                    # update existing event
                    updated_event = update_event(db, event_data['id'], event_payload, user_id)
                    st.session_state.event_success_message = f"Event '{updated_event['title']}' updated successfully!"
                    st.session_state.editing_event_id = None
                    st.session_state.selected_location = ""  # Clear location
                else:
                    # create new event
                    new_event = create_event(db, event_payload, user_id)
                    st.session_state.event_success_message = f"Event '{new_event['title']}' created successfully!"
                    st.session_state.selected_location = ""  # Clear location
                
                st.rerun()
                
            except PermissionDenied:
                st.session_state.event_error_message = "You don't have permission to modify this event"
                st.rerun()
            except Exception as e:
                st.session_state.event_error_message = f"Error saving event: {str(e)}"
                st.rerun()
        
        if edit_mode and cancel_button:
            st.session_state.editing_event_id = None
            clear_event_messages()
            st.rerun()

def show_event_card(event: Dict[str, Any], user_id: str, db, show_actions: bool = True):
    """
    display a single event card.
    
    event: Event data dictionary
    user_id: Current user's ID
    db: Firestore database client
    show_actions: Whether to show edit/delete actions
    """
    with st.container():
        # event header
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {event.get('title', 'Untitled Event')}")
            
            # event status badge
            if event.get('published'):
                st.markdown("🟢 **Published**")
            else:
                st.markdown("🟡 **Draft**")
        
        with col2:
            if show_actions and event.get('created_by') == user_id:
                if st.button("Edit", key=f"edit_{event['id']}"):
                    st.session_state.editing_event_id = event['id']
                    st.session_state.active_tab = 0 # switch to create event tab
                    clear_event_messages()
                    st.rerun()
        
        # event details
        st.markdown(f"**Location:** {event.get('location', 'TBA')}")
        
        # capacity
        if event.get('capacity'):
            st.markdown(f"**Capacity:** {event.get('capacity')} people")
        
        # parse and display times
        start_date, start_time = parse_iso_to_datetime(event.get('start_time'))
        
        # check if end_time exists (for backward compatibility)
        if event.get('end_time'):
            _, end_time = parse_iso_to_datetime(event.get('end_time'))
            st.markdown(f"**Date:** {start_date.strftime('%B %d, %Y')}")
            st.markdown(f"**Time:** {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}")
        else:
            st.markdown(f"**Start:** {start_date.strftime('%B %d, %Y')} at {start_time.strftime('%I:%M %p')}")
        
        if event.get('description'):
            with st.expander("Event Description"):
                st.write(event['description'])
        
        # categories
        if event.get('categories'):
            st.markdown("**Categories:** " + ", ".join(event['categories']))
        
        # action buttons for event owner
        if show_actions and event.get('created_by') == user_id:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if event.get('published'):
                    if st.button("📝 Unpublish", key=f"unpub_{event['id']}"):
                        try:
                            unpublish_event(db, event['id'], user_id)
                            st.session_state.event_success_message = "Event unpublished"
                            st.rerun()
                        except Exception as e:
                            st.session_state.event_error_message = f"Error: {str(e)}"
                            st.rerun()
                else:
                    if st.button("✅ Publish", key=f"pub_{event['id']}"):
                        try:
                            publish_event(db, event['id'], user_id)
                            st.session_state.event_success_message = "Event published"
                            st.rerun()
                        except Exception as e:
                            st.session_state.event_error_message = f"Error: {str(e)}"
                            st.rerun()
            
            with col2:
                if st.button("🗑️ Delete", type="primary",key=f"del_{event['id']}"):
                    st.session_state[f"confirm_delete_{event['id']}"] = True
            
            # confirmation dialog for delete
            if st.session_state.get(f"confirm_delete_{event['id']}", False):
                st.warning(f"Are you sure you want to delete '{event['title']}'?")
                col_yes, col_no = st.columns(2)
                
                with col_yes:
                    if st.button("Yes, delete", type="primary", key=f"confirm_yes_{event['id']}"):
                        try:
                            delete_event(db, event['id'], user_id)
                            st.session_state.event_success_message = "Event deleted successfully"
                            st.session_state.pop(f"confirm_delete_{event['id']}")
                            st.rerun()
                        except Exception as e:
                            st.session_state.event_error_message = f"Error: {str(e)}"
                            st.rerun()
                
                with col_no:
                    if st.button("Cancel", key=f"confirm_no_{event['id']}"):
                        st.session_state.pop(f"confirm_delete_{event['id']}")
                        st.rerun()
        
        st.divider()

def show_my_events_list(db, user_id: str):
    # Display list of user's events.
    st.markdown("<h2 style='text-align: center;'>" \
    "My Events</h2>", unsafe_allow_html=True)
    
    try:
        # get all events
        all_events, _ = list_events(db, published=None)
        
        # filter to only user's events
        user_events = [e for e in all_events if e.get('created_by') == user_id]
        
        if not user_events:
            st.info("You haven't created any events yet. Create your first World Cup event above!")
            return
        
        # Separate published and draft events
        published_events = [e for e in user_events if e.get('published')]
        draft_events = [e for e in user_events if not e.get('published')]
        
        # display published events
        if published_events:
            st.markdown("#### :green[Published Events]")
            for event in published_events:
                show_event_card(event, user_id, db)
        
        # display draft events
        if draft_events:
            st.markdown("#### :red[Draft Events]")
            for event in draft_events:
                show_event_card(event, user_id, db)
                
    except Exception as e:
        st.error(f"Error loading events: {str(e)}")

def show_event_management_interface():
    """Main interface for event creation and management."""
    initialize_event_session_state()
    
    # Check if user is logged in
    if not st.session_state.get('user_info'):
        st.warning("Please sign in to create and manage events.")
        return
    
    user_id = st.session_state.user_info.get('localId')
    db = get_db()
    
    st.markdown("<h1 style='text-align: center;'>" \
    "Event Management</h1>", unsafe_allow_html=True)
    
    # Display success/error messages
    if st.session_state.event_success_message:
        st.success(st.session_state.event_success_message)
        st.session_state.event_success_message = None
    
    if st.session_state.event_error_message:
        st.error(st.session_state.event_error_message)
        st.session_state.event_error_message = None
    
    # Check user's event count
    all_events, _ = list_events(db, published=None, limit=100)
    user_events = [e for e in all_events if e.get('created_by') == user_id]
    user_event_count = len(user_events)

    # show event count status
    if user_event_count >= 3:
        st.warning(f"⚠️ You have reached the maximum limit of 3 events ({user_event_count}/3)")
    
    # manual tab navigation using buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Event", 
                    type="primary" if st.session_state.active_tab == 0 else "secondary",
                    use_container_width=True,
                    key="tab_create"):
            st.session_state.active_tab = 0
            st.rerun()
    
    with col2:
        if st.button("My Events", 
                    type="primary" if st.session_state.active_tab == 1 else "secondary",
                    use_container_width=True,
                    key="tab_my_events"):
            st.session_state.active_tab = 1
            st.rerun()
    
    st.divider()
        
    # show content based on active tab
    if st.session_state.active_tab == 0:
        # create Event tab content
        # check if user has reached the limit
        if user_event_count >= 3 and not st.session_state.editing_event_id:
            st.info("💡 Delete an existing event from the 'My Events' tab to create a new one.")
        else:
            # check if editing an existing event
            if st.session_state.editing_event_id:
                try:
                    event_data = get_event(db, st.session_state.editing_event_id)
                    show_event_creation_form(db, user_id, edit_mode=True, event_data=event_data)
                except EventNotFound:
                    st.error("Event not found")
                    st.session_state.editing_event_id = None
                    st.rerun()
            else:
                show_event_creation_form(db, user_id, edit_mode=False)
    
    else:
        # My Events tab content
        show_my_events_list(db, user_id)