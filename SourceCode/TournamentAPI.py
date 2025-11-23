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
from datetime import date
from typing import Dict, Any, Optional


# Hard-coded tournament selection so the UI can display something.
LEAGUE_ID = 39   # e.g., Premier League
SEASON = 2024


def get_tournament_summary(today: Optional[date] = None) -> Dict[str, Any]:
    """
    TEMP STUB.

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

    Right now we just return empty lists so the UI can show "no data" messages.
    """
    return {
        "today": [],
        "recent": [],
        "upcoming": [],
        "standings": [],
    }



def get_fixtures(*args, **kwargs):
    """Stub: should return a list of fixture dicts."""
    return []


def get_standings():
    """Stub: should return a list of group standings as described above."""
    return []


def get_match_detail(fixture_id: int):
    """Stub: should return a fixture dict for a single match, or None."""
    return None


def get_match_events(fixture_id: int):
    """Stub: should return a list of event dicts (goals, cards, subs)."""
    return []
