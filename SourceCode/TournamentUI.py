# TournamentUI.py

"""
Streamlit Tournament Info UI for HomeStand.

Frontend responsibilities:
  - Call TournamentAPI.get_tournament_summary()
  - Render sections:
      - Today's Fixtures
      - Recent Results
      - Upcoming Fixtures
      - Group / League Standings
  - Support "All Teams" vs "My Teams" view using profile favTeams

Backend isn't yet implemented so TournamentUI is coded so that it
will still function without the backend working. the UI will
show a friendly message instead of crashing.
"""

from __future__ import annotations
from typing import Dict, Any, List
from datetime import date, datetime

import streamlit as st

from TournamentAPI import get_tournament_summary, LEAGUE_ID, SEASON
from ProfilesAPI import get_profile


def _team_in_favorites(team_name: str, fav_teams: List[str]) -> bool:
    """
    Check if a team name matches any favorite team string
    by simple case-insensitive substring match.

    This avoids needing exact ID mapping and works fine for demo purposes.
    """
    if not fav_teams:
        return False

    name_lower = (team_name or "").lower()
    for fav in fav_teams:
        if fav.lower() in name_lower:
            return True
    return False


def _filter_fixtures_by_my_teams(fixtures: List[Dict[str, Any]], fav_teams: List[str]) -> List[Dict[str, Any]]:
    """
    Keep only fixtures where either home or away team appears in fav_teams.

    Works safely even if fixtures are missing fields, thanks to .get chains.
    """
    if not fav_teams:
        return fixtures

    filtered = []
    for f in fixtures:
        teams = f.get("teams", {})
        home = teams.get("home", {}).get("name", "") or ""
        away = teams.get("away", {}).get("name", "") or ""
        if _team_in_favorites(home, fav_teams) or _team_in_favorites(away, fav_teams):
            filtered.append(f)
    return filtered


def _status_badge(status_short: str) -> str:
    """
    Map short status codes (e.g. 'NS', 'FT') to a friendly badge text.
    We keep this small and defensive so it never crashes.
    """
    code = (status_short or "").upper()
    if code == "NS":
        return "🟦 NS"
    if code in ("FT", "AET", "PEN"):
        return "🟩 FT"
    if code in ("PST", "CANC", "ABD"):
        return "🟥 Postponed"
    if code in ("1H", "2H", "HT", "ET", "BT"):
        return "🟨 Live"
    return code or "?"


def _render_fixture_card(f: Dict[str, Any]):
    """
    Render one match fixture card.

    Designed to tolerate missing keys so stubbed / partial data won't crash it.
    """
    fixture = f.get("fixture", {}) or {}
    teams = f.get("teams", {}) or {}
    goals = f.get("goals", {}) or {}
    league = f.get("league", {}) or {}
    venue = f.get("venue", {}) or {}

    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    status = fixture.get("status", {}) or {}
    status_short = status.get("short")
    badge = _status_badge(status_short)

    dt_iso = fixture.get("date") or ""
    date_str = ""
    time_str = ""
    if dt_iso:
        try:
            dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            # Fall back to raw string if parsing fails
            date_str = dt_iso

    home_name = home.get("name", "Home")
    away_name = away.get("name", "Away")

    st.markdown(f"#### {home_name} vs {away_name}")
    st.caption(
        f"{league.get('round', '')} • "
        f"{venue.get('name', 'Venue TBA')} "
        f"({venue.get('city', '')})"
    )

    # Score line (if available)
    if goals.get("home") is not None and goals.get("away") is not None:
        st.markdown(f"**Score:** {goals['home']} - {goals['away']}   ({badge})")
    elif date_str or time_str:
        st.markdown(f"**Kickoff:** {date_str} • {time_str}   ({badge})")
    else:
        st.markdown(f"**Status:** {badge}")

    fixture_id = fixture.get("id", "N/A")
    st.caption(f"Fixture ID: {fixture_id}")
    st.divider()


def _render_standings_table(groups: List[Dict[str, Any]]):
    """
    Render group/league standings from the structure described in TournamentAPI.

    Uses basic Streamlit table rendering (no extra deps) so it can't
    crash due to missing libraries.
    """
    for group in groups:
        group_name = group.get("group", "Standings")
        rows = group.get("rows", []) or []

        if not rows:
            continue

        st.markdown(f"#### {group_name}")

        # Prepare rows as list-of-lists for st.table
        header = ["Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]
        table_rows = []
        for row in rows:
            table_rows.append([
                #row.get("rank", ""),
                row.get("team_name", ""),
                row.get("played", ""),
                row.get("win", ""),
                row.get("draw", ""),
                row.get("lose", ""),
                row.get("gf", ""),
                row.get("ga", ""),
                row.get("gd", ""),
                row.get("points", ""),
            ])

        st.table([header] + table_rows)
        st.divider()


def show_tournament_page():
    """
    Main UI entrypoint for Tournament Info.
    """
    user = st.session_state.get("user_info") or {}
    uid = user.get("localId")

    # Load profile for favTeams (if user is logged in)
    fav_teams: List[str] = []
    if uid:
        try:
            profile = get_profile(uid)
            fav_teams = profile.get("favTeams", []) or []
        except Exception:
            # If profile backend ever fails, just fall back to empty favorites
            fav_teams = []

    st.title("Tournament Information")
    st.caption(f"League ID: {LEAGUE_ID} • Season: {SEASON}")

    # Quick filter: All / My Teams
    view_mode = st.radio(
        "View fixtures for:",
        options=["All Teams", "My Teams"],
        horizontal=True,
        index=0,
    )

    # Fetch summary from backend stub
    try:
        with st.spinner("Loading tournament data…"):
            summary = get_tournament_summary(today=date.today())
    except Exception as e:
        # If backend is broken/not implemented yet, we fail softly.
        st.info(
            "Tournament data backend is not implemented yet. "
            "Once the backend is ready, this page will show live fixtures and standings."
        )
        st.caption(f"(Backend error: {e})")
        return

    # Be defensive about missing keys / wrong shapes
    if not isinstance(summary, dict):
        st.info("Tournament data is not available yet (unexpected backend format).")
        return

    today_fixtures = summary.get("today") or []
    recent_results = summary.get("recent") or []
    upcoming = summary.get("upcoming") or []
    standings = summary.get("standings") or []

    # Apply "My Teams" filter if selected
    if view_mode == "My Teams":
        today_fixtures = _filter_fixtures_by_my_teams(today_fixtures, fav_teams)
        recent_results = _filter_fixtures_by_my_teams(recent_results, fav_teams)
        upcoming = _filter_fixtures_by_my_teams(upcoming, fav_teams)

    # -------- Sections --------

    st.subheader("Today's Fixtures")
    if not today_fixtures:
        st.info(
            "No fixtures available for today yet. "
        )
    else:
        for f in today_fixtures:
            _render_fixture_card(f)

    st.subheader("Recent Results")
    if not recent_results:
        st.info("No recent results available.")
    else:
        for f in recent_results:
            _render_fixture_card(f)

    st.subheader("Upcoming Fixtures")
    if not upcoming:
        st.info("No upcoming fixtures available.")
    else:
        for f in upcoming:
            _render_fixture_card(f)

    st.subheader("Group / League Standings")
    if not standings:
        st.info(
            "Standings are not available yet. "
        )
    else:
        _render_standings_table(standings)