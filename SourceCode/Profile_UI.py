# Profile_UI.py
"""
Streamlit Profile UI for HomeStand (frontend only).
Uses ProfilesAPI for all data access.

Features:
- Ensure default profile on first sign-in.
- View/edit: displayName, bio, homeCity, favTeams, visibility.
- Avatar via URL (string stored in Firestore)
- Optional file upload hook (uses ProfilesAPI.upload_avatar if/when implemented).

No backend changes required for the above.
"""

from typing import Dict, Any, List, Optional

import streamlit as st
from ProfilesAPI import ( #backend portion that needs to be implemented
    ensure_default_profile,
    save_profile,
    upload_avatar as backend_upload,
)

# Choose a small, clear set. You can extend or load from Firestore later.
FAV_TEAM_OPTIONS = [
    "USA", "Mexico", "Canada", "Brazil", "Argentina", "France", "Spain", "Germany",
    "England", "Italy", "Portugal", "Netherlands", "Japan", "South Korea", "Morocco"
]

# ---------------- UI bits ----------------
def _profile_header(title: str):
    st.markdown(f"### {title}")


def _avatar_block(avatar_url: str, display_name: str):
    c1, c2 = st.columns([1, 3])
    with c1:
        if avatar_url:
            st.image(avatar_url, width=150) #, use_container_width=True) this caused an error with using a url
        else:
            # Simple placeholder
            st.markdown(
                """
                <div style="
                    width:100%;
                    aspect-ratio:1/1;
                    border-radius:16px;
                    background:#EEE;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:28px;
                    color:#666;
                    border:1px solid #DDD;">
                    👤
                </div>
                """,
                unsafe_allow_html=True,
            )
    with c2:
        st.markdown(f"**{display_name or 'User'}**")
        st.caption("Your public profile on HomeStand")


def render_profile_card(profile: Dict[str, Any]):
    with st.container():
        _profile_header("My Profile")
        _avatar_block(profile.get("avatarUrl", ""), profile.get("displayName", ""))
        st.write(profile.get("bio") or "_No bio yet._")

        meta = []
        city = profile.get("homeCity")
        if city:
            meta.append(f"📍 {city}")

        teams: List[str] = profile.get("favTeams") or []
        if teams:
            meta.append("🏳️ " + ", ".join(teams))

        vis = profile.get("visibility") or "Public"
        meta.append("🌐 Public" if vis == "Public" else "🔒 Private")

        if meta:
            st.caption(" | ".join(meta))

        st.divider()


def avatar_uploader(uid: str, current_url: str) -> Optional[str]:
    """
    UI for avatar:
      - URL field (always supported)
      - File uploader (optional; uses backend_upload if implemented)
    Returns a new URL (or None if unchanged).
    """
    st.markdown("#### Avatar")
    url = st.text_input("Avatar URL (https://…)", value=current_url or "", placeholder="https://example.com/me.png")
    uploaded = st.file_uploader("Or upload image (PNG/JPEG)", type=["png", "jpg", "jpeg"])

    new_url = None

    if uploaded is not None:
        file_bytes = uploaded.read()
        mime = uploaded.type or "application/octet-stream"
        with st.spinner("Uploading avatar…"):
            maybe_url = backend_upload(uid, file_bytes, mime)  # returns URL or None
        if maybe_url:
            st.success("Avatar uploaded!")
            new_url = maybe_url
        else:
            st.info("Avatar upload isn’t enabled yet. Use the URL field for now.")

    # If URL input changed, prefer it
    if url and url != current_url:
        new_url = url

    return new_url


# ---------------- Main entrypoint ----------------
def show_profile_page():
    """
    Call from your logged-in view.
    - Ensures default profile exists
    - Shows read-only card + Edit flow
    """
    user = st.session_state.get("user_info") or {}
    uid = user.get("localId")
    if not uid:
        st.warning("Please sign in to view your profile.")
        return

    # Ensure a profile doc exists (creates one if missing)
    profile = ensure_default_profile(uid, user_info=user)

    # UI state
    if "editing_profile" not in st.session_state:
        st.session_state.editing_profile = False
    if "profile_flash" not in st.session_state:
        st.session_state.profile_flash = None

    # Flash messages
    if st.session_state.profile_flash:
        kind, msg = st.session_state.profile_flash
        {"ok": st.success, "warn": st.warning, "err": st.error}.get(kind, st.info)(msg)
        st.session_state.profile_flash = None

    # Card
    render_profile_card(profile)

    # Toggle
    left, _ = st.columns([1, 6])
    with left:
        if st.button(("✅ Done" if st.session_state.editing_profile else "✏️ Edit Profile"),
                     use_container_width=True):
            st.session_state.editing_profile = not st.session_state.editing_profile
            st.rerun()

    if not st.session_state.editing_profile:
        return

    # -------- Edit Form --------
    st.markdown("#### Edit Profile")
    with st.form("edit_profile_form", clear_on_submit=False):
        display_name = st.text_input("Display Name *", value=profile.get("displayName", ""))
        bio = st.text_area("Bio", value=profile.get("bio", ""), max_chars=280, height=100)
        home_city = st.text_input("Home City", value=profile.get("homeCity", ""))

        # Teams: allow Multiselect + one custom text field that gets added on Save
        fav = st.multiselect("Favorite Teams", options=FAV_TEAM_OPTIONS, default=profile.get("favTeams", []))
        custom_team = st.text_input("Add a custom team (optional)")

        visibility = st.selectbox("Profile Visibility", options=["Public", "Private"],
                                  index=(0 if (profile.get("visibility", "Public") == "Public") else 1))

        # Avatar section
        new_avatar_url = avatar_uploader(uid, current_url=profile.get("avatarUrl", ""))

        c1, c2 = st.columns(2)
        with c1:
            save_clicked = st.form_submit_button("💾 Save Changes", type="primary")
        with c2:
            cancel_clicked = st.form_submit_button("Cancel")

    # Actions
    if cancel_clicked and not save_clicked:
        st.session_state.editing_profile = False
        st.rerun()

    if save_clicked:
        # Lightweight validation
        if not display_name.strip():
            st.session_state.profile_flash = ("err", "Display Name is required.")
            st.rerun()

        if custom_team.strip():
            if custom_team not in fav:
                fav = fav + [custom_team.strip()]

        updates: Dict[str, Any] = {
            "displayName": display_name.strip(),
            "bio": bio.strip(),
            "homeCity": home_city.strip(),
            "favTeams": fav,
            "visibility": visibility,
        }
        if new_avatar_url is not None:
            updates["avatarUrl"] = new_avatar_url.strip()

        try:
            _ = save_profile(uid, updates)
            st.session_state.profile_flash = ("ok", "Profile saved!")
            st.session_state.editing_profile = False
            st.rerun()
        except Exception as e:
            st.session_state.profile_flash = ("err", f"Failed to save profile: {e}")
            st.rerun()
