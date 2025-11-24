# TournamentAPI.py
"""
Stub backend for tournament information.

Real implementation will:
  - Call API-FOOTBALL (API-Sports)
  - Fetch fixtures (schedule/results) and standings
  - Map responses into the structures returned here

For now, these stubs return safe empty structures so that the UI loads
without crashing.
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
import requests
import streamlit as st
import hashlib
import json

# Hard-coded tournament selection so the UI can display something.
LEAGUE_ID = 39   # e.g., Premier League
SEASON = 2022

TOURNAMENT_API_KEY = st.secrets["tournament_api"]["TOURNAMENT_API_KEY"]

BASE_URL = "https://v3.football.api-sports.io"

headers = {
  'x-apisports-key': TOURNAMENT_API_KEY,
}


class APICache:
    """
    Simple in-memory cache for API responses with 1-hour expiration.
    Uses Streamlit session state to persist cache across reruns.
    """
    
    CACHE_EXPIRATION_HOURS = 1
    CACHE_KEY_PREFIX = "api_cache_"
    
    @staticmethod
    def _generate_cache_key(endpoint: str, params: Dict[str, Any]) -> str:
        """Generate a unique cache key based on endpoint and parameters."""
        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{APICache.CACHE_KEY_PREFIX}{endpoint}_{param_hash}"
    
    @staticmethod
    def get(endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response if it exists and hasn't expired.
        
        Returns:
            Cached response dict or None if cache miss or expired.
        """
        cache_key = APICache._generate_cache_key(endpoint, params)
        
        if cache_key not in st.session_state:
            return None
        
        cache_entry = st.session_state[cache_key]
        cached_time = cache_entry.get("timestamp")
        cached_data = cache_entry.get("data")
        
        # Check if cache has expired
        if cached_time:
            elapsed = datetime.now() - cached_time
            if elapsed > timedelta(hours=APICache.CACHE_EXPIRATION_HOURS):
                print(f"Cache expired for {endpoint}. Fetching fresh data.")
                del st.session_state[cache_key]
                return None
        
        print(f"Cache HIT for {endpoint}")
        return cached_data
    
    @staticmethod
    def set(endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> None:
        """
        Store response in cache with current timestamp.
        
        Args:
            endpoint: API endpoint name
            params: Request parameters
            data: Response data to cache
        """
        cache_key = APICache._generate_cache_key(endpoint, params)
        st.session_state[cache_key] = {
            "timestamp": datetime.now(),
            "data": data,
        }
        print(f"Cache MISS for {endpoint}. Caching response.")
    
    @staticmethod
    def clear_all() -> None:
        """Clear all cached API responses."""
        keys_to_delete = [key for key in st.session_state.keys() if key.startswith(APICache.CACHE_KEY_PREFIX)]
        for key in keys_to_delete:
            del st.session_state[key]
        print(f"Cleared {len(keys_to_delete)} cache entries.")

def get_tournament_summary(today: Optional[date] = None) -> Dict[str, Any]:
    """
    Fetch tournament summary including today's fixtures, recent results, upcoming fixtures, and standings.
    
    Expected final shape (for reference):
        {
          "today":    [<fixture dicts>],
          "recent":   [<fixture dicts>],
          "upcoming": [<fixture dicts>],
          "standings": [
              {
                "group": "Group A" or "Premier League",
                "rows": [
                    {
                      "rank": int,
                      "team_id": int,
                      "team_name": str,
                      "played": int,
                      "win": int,
                      "draw": int,
                      "lose": int,
                      "gf": int,
                      "ga": int,
                      "gd": int,
                      "points": int,
                    },
                    ...
                ]
              },
              ...
          ]
        }
    """
    standings = get_standings()
    print("Standings fetched:", standings)
    
    # Fetch today's fixtures
    if today is None:
        today = date.today()
    
    today_str = today.isoformat()
    today_fixtures = get_fixtures(date=today_str)
    
    # Fetch recent results (last 5 finished fixtures)
    recent_fixtures = get_fixtures(status="FT")
    recent_results = recent_fixtures[-5:] if recent_fixtures else []
    
    # Fetch upcoming fixtures (next fixtures with NS status)
    upcoming_fixtures = get_fixtures(status="NS")
    upcoming = upcoming_fixtures[:5] if upcoming_fixtures else []

    return {
        "today": today_fixtures,
        "recent": recent_results,
        "upcoming": upcoming,
        "standings": standings,
    }



def get_fixtures(league_id: int = LEAGUE_ID, season: int = SEASON, status: Optional[str] = None, date: Optional[str] = None) -> list:
    """
    Fetch fixtures from API-FOOTBALL for a given league and season.
    Results are cached for 1 hour.
    
    Returns a list of fixture dicts matching the UI format:
    [
        {
            "fixture": {"id": int, "date": str (ISO), "status": {"short": str}},
            "league": {"round": str},
            "venue": {"name": str, "city": str},
            "teams": {
                "home": {"name": str},
                "away": {"name": str}
            },
            "goals": {"home": int or None, "away": int or None}
        },
        ...
    ]
    
    Parameters:
    - league_id: League ID (default: LEAGUE_ID)
    - season: Season year (default: SEASON)
    - status: Filter by status (e.g., "NS" for not started, "FT" for finished, "PST" for postponed)
    - date: Filter by specific date (YYYY-MM-DD format)
    """
    fixtures_url = f"{BASE_URL}/fixtures"
    params = {
        "league": league_id,
        "season": season,
    }
    
    # Add optional filters
    if status:
        params["status"] = status
    if date:
        params["date"] = date
    
    # Check cache first
    cached_result = APICache.get("fixtures", params)
    if cached_result is not None:
        return cached_result
    
    try:
        response = requests.get(fixtures_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Fixtures API Response Status: {response.status_code}")
        print(f"Number of fixtures: {data.get('results', 0)}")
        
        if not data.get("response"):
            print("No fixtures in response.")
            return []
        
        # Transform to UI format
        fixtures = []
        for fixture_data in data["response"]:
            fixture = fixture_data.get("fixture", {})
            teams = fixture_data.get("teams", {})
            goals = fixture_data.get("goals", {})
            league = fixture_data.get("league", {})
            venue = fixture_data.get("venue", {})
            
            fixtures.append({
                "fixture": {
                    "id": fixture.get("id"),
                    "date": fixture.get("date"),
                    "status": fixture.get("status", {}),
                },
                "league": {
                    "round": league.get("round", ""),
                },
                "venue": {
                    "name": venue.get("name", "Venue TBA"),
                    "city": venue.get("city", ""),
                },
                "teams": {
                    "home": {
                        "name": teams.get("home", {}).get("name", "Home"),
                    },
                    "away": {
                        "name": teams.get("away", {}).get("name", "Away"),
                    },
                },
                "goals": {
                    "home": goals.get("home"),
                    "away": goals.get("away"),
                },
            })
        
        # Cache the result
        APICache.set("fixtures", params, fixtures)
        return fixtures
    
    except Exception as e:
        print(f"Exception in get_fixtures: {e}")
        st.warning(f"Error fetching fixtures: {e}")
        return []


def get_standings():
    """
    Fetch league standings from API-FOOTBALL and transform to UI format.
    Results are cached for 1 hour.
    
    Returns a list of groups, each with standings rows matching the expected format:
    [
        {
            "group": str,
            "rows": [
                {
                    "rank": int,
                    "team_id": int,
                    "team_name": str,
                    "played": int,
                    "win": int,
                    "draw": int,
                    "lose": int,
                    "gf": int,
                    "ga": int,
                    "gd": int,
                    "points": int,
                },
                ...
            ]
        },
        ...
    ]
    """
    standings_url = f"{BASE_URL}/standings"
    params = {
        "league": LEAGUE_ID,
        "season": SEASON,
    }
    
    # Check cache first
    cached_result = APICache.get("standings", params)
    if cached_result is not None:
        return cached_result
    
    try:
        response = requests.get(standings_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Print statements for debugging
        print(f"API Response Status: {response.status_code}")
        print(f"API Response Keys: {data.keys()}")
        print(f"API Errors: {data.get('errors', {})}")
        print(f"API Response Count: {len(data.get('response', []))}")
        
        # API response structure: data['response'] is a list with one element
        # data['response'][0]['league']['standings'] is a list of groups
        if not data.get("response"):
            print("No standings data in response.")
            st.warning(f"API returned no standings data. Errors: {data.get('errors', {})}")
            return []
        
        league_data = data["response"][0].get("league", {})
        standings_list = league_data.get("standings", [])
        
        print(f"Number of groups: {len(standings_list)}")
        
        # Transform to UI format
        result = []
        for group_list in standings_list:
            group_name = group_list[0].get("group", "Standings") if group_list else "Standings"
            rows = []
            
            for entry in group_list:
                team = entry.get("team", {})
                all_entries = entry.get("all", {})
                
                # Handle missing goals data - calculate from home and away if needed
                goals_for = all_entries.get("for")
                goals_against = all_entries.get("against")
                
                # Ensure goals_for and goals_against are integers
                if not isinstance(goals_for, int):
                    goals_for = 0
                if not isinstance(goals_against, int):
                    goals_against = 0
                
                rows.append({
                    "rank": entry.get("rank"),
                    "team_id": team.get("id"),
                    "team_name": team.get("name"),
                    "played": all_entries.get("played", 0),
                    "win": all_entries.get("win", 0),
                    "draw": all_entries.get("draw", 0),
                    "lose": all_entries.get("lose", 0),
                    "gf": goals_for or 0,
                    "ga": goals_against or 0,
                    "gd": entry.get("goalsDiff", 0),
                    "points": entry.get("points", 0),
                })
            
            result.append({
                "group": group_name,
                "rows": rows,
            })
        print("Transformed standings:", result)
        
        # Cache the result
        APICache.set("standings", params, result)
        return result
    
    except Exception as e:
        print(f"Exception in get_standings: {e}")
        st.warning(f"Error fetching standings: {e}")
        return []


def get_match_detail(fixture_id: int):
    """
    Fetch detailed information for a single fixture.
    Results are cached for 1 hour.
    
    Returns a fixture dict matching the UI format, or None if not found.
    """
    fixtures_url = f"{BASE_URL}/fixtures"
    params = {
        "id": fixture_id,
    }
    
    # Check cache first
    cached_result = APICache.get("match_detail", params)
    if cached_result is not None:
        return cached_result
    
    try:
        response = requests.get(fixtures_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Match Detail API Response Status: {response.status_code}")
        
        if not data.get("response") or len(data["response"]) == 0:
            print(f"No fixture found with ID {fixture_id}.")
            return None
        
        fixture_data = data["response"][0]
        fixture = fixture_data.get("fixture", {})
        teams = fixture_data.get("teams", {})
        goals = fixture_data.get("goals", {})
        league = fixture_data.get("league", {})
        venue = fixture_data.get("venue", {})
        
        result = {
            "fixture": {
                "id": fixture.get("id"),
                "date": fixture.get("date"),
                "status": fixture.get("status", {}),
            },
            "league": {
                "round": league.get("round", ""),
            },
            "venue": {
                "name": venue.get("name", "Venue TBA"),
                "city": venue.get("city", ""),
            },
            "teams": {
                "home": {
                    "name": teams.get("home", {}).get("name", "Home"),
                },
                "away": {
                    "name": teams.get("away", {}).get("name", "Away"),
                },
            },
            "goals": {
                "home": goals.get("home"),
                "away": goals.get("away"),
            },
        }
        
        # Cache the result
        APICache.set("match_detail", params, result)
        return result
    
    except Exception as e:
        print(f"Exception in get_match_detail: {e}")
        st.warning(f"Error fetching match detail: {e}")
        return None


def get_match_events(fixture_id: int):
    """
    Fetch events (goals, cards, substitutions) for a fixture.
    Results are cached for 1 hour.
    
    Returns a list of event dicts:
    [
        {
            "time": {"elapsed": int},
            "team": {"name": str},
            "player": {"name": str},
            "type": str (e.g., "Goal", "Card", "Subst"),
            "detail": str (e.g., "Normal Goal", "Yellow Card"),
        },
        ...
    ]
    """
    events_url = f"{BASE_URL}/fixtures/events"
    params = {
        "fixture": fixture_id,
    }
    
    # Check cache first
    cached_result = APICache.get("match_events", params)
    if cached_result is not None:
        return cached_result
    
    try:
        response = requests.get(events_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"Match Events API Response Status: {response.status_code}")
        print(f"Number of events: {data.get('results', 0)}")
        
        if not data.get("response"):
            print(f"No events found for fixture {fixture_id}.")
            return []
        
        # Transform to UI format
        events = []
        for event_data in data["response"]:
            time = event_data.get("time", {})
            team = event_data.get("team", {})
            player = event_data.get("player", {})
            
            events.append({
                "time": {
                    "elapsed": time.get("elapsed"),
                },
                "team": {
                    "name": team.get("name", "Unknown"),
                },
                "player": {
                    "name": player.get("name", "Unknown"),
                },
                "type": event_data.get("type", ""),
                "detail": event_data.get("detail", ""),
            })
        
        # Cache the result
        APICache.set("match_events", params, events)
        return events
    
    except Exception as e:
        print(f"Exception in get_match_events: {e}")
        st.warning(f"Error fetching match events: {e}")
        return []
