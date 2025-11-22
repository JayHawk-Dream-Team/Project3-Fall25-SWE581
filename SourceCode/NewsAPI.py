# NewsAPI.py
# Backend news-fetching module for HomeStand
#
# Responsibilities:
#   - Fetch live sports/tournament articles from NewsAPI.org
#   - Provide search, filter, trending, and latest headlines
#   - Return UI-ready dictionaries for NewsUI.py
#   - Gracefully degrade to mock data if API fails or API key missing
#
# Author: Yoseph Ephrem (Backend)
# Sprint 3 - News Feature

import requests
from datetime import datetime
import streamlit as st

# ----------------------------
# 🔑 INSERT YOUR NEWSAPI.ORG KEY HERE
# ----------------------------
NEWS_API_KEY = st.secrets["newsapi"]["NEWS_API_KEY"]

# Base URL for soccer / world cup content
BASE_URL = "https://newsapi.org/v2/everything"
TOP_HEADLINES_URL = "https://newsapi.org/v2/top-headlines"


# -----------------------------------------------------
# INTERNAL: Format JSON from external API → UI-Friendly dict
# -----------------------------------------------------
# -----------------------------------------------------
# INTERNAL: Format JSON from external API → UI-Friendly dict
# -----------------------------------------------------
def _format_article(a):
    """
    Convert NewsAPI-style JSON article to the exact format expected by NewsUI.py.
    Ensures all fields exist and timestamp is converted into the UI-required format.
    """

    # Raw timestamp from NewsAPI (ISO format, may end with "Z")
    published_at = a.get("publishedAt")

    # Default timestamp string in case conversion fails
    timestamp_fmt = "Unknown"

    if published_at:
        try:
            # Convert ISO8601 → Python datetime object
            # Example: "2025-01-13T12:34:56Z"
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

            # Convert datetime → UI format "YYYY-MM-DD HH:MM"
            timestamp_fmt = dt.strftime("%Y-%m-%d %H:%M")

        except Exception:
            # If conversion fails, fallback to raw API timestamp
            timestamp_fmt = published_at

    # Return a clean, UI-ready dictionary
    return {
        "title": a.get("title", "Untitled"),  # fallback if missing
        "source": a.get("source", {}).get("name", "Unknown"),
        "summary": a.get("description", "No summary available."),
        "image": a.get("urlToImage"),         # may be None
        "timestamp": timestamp_fmt,           # formatted timestamp
        "url": a.get("url"),                  # link to full article
    }


# -----------------------------------------------------
# INTERNAL: fallback data (used when API errors)
# -----------------------------------------------------
def _fallback_articles():
    """
    Returns static sample articles when:
      - the API key is missing
      - NewsAPI.org rate-limits (429)
      - Network issues
      - Unexpected API errors

    This ensures the News page never breaks and always displays something.
    """
    return [
        {
            "title": "Spain Advances to World Cup Semifinals",
            "source": "ESPN",
            "summary": "Spain secures a dramatic victory in extra time, moving on to face France.",
            "image": "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg",
            "timestamp": "2025-01-13 19:30",
            "url": "https://www.espn.com",
        },
        {
            "title": "Injury Report: Key Striker Out Before Quarterfinals",
            "source": "BBC Sports",
            "summary": "Team medical staff confirm the injury will keep the star out for at least 2 weeks.",
            "image": "https://images.pexels.com/photos/6097714/pexels-photo-6097714.jpeg",
            "timestamp": "2025-01-14 10:15",
            "url": "https://www.bbc.com/sport",
        },
        {
            "title": "Top 5 Goals of the Group Stage",
            "source": "ESPN",
            "summary": "A look back at the most spectacular goals of the group round.",
            "image": "https://images.pexels.com/photos/114296/pexels-photo-114296.jpeg",
            "timestamp": "2025-01-10 08:45",
            "url": "https://www.espn.com",
        },
    ]


# -----------------------------------------------------
# CORE HELPERS FOR FETCHING NEWS
# -----------------------------------------------------
def _fetch_from_newsapi(params):
    """
    Execute a request to NewsAPI.org and gracefully fallback if something goes wrong.
    """

    # If no real API key is set, fallback immediately
    if NEWS_API_KEY == "YOUR_NEWSAPI_KEY_HERE":
        return _fallback_articles()

    try:
        # Send GET request with dynamic parameters
        resp = requests.get(BASE_URL, params=params, timeout=5)

        # Parse JSON payload
        data = resp.json()

        # If API returns "status": "error" → fallback
        if data.get("status") != "ok":
            return _fallback_articles()

        # Extract list of articles from API response
        articles_raw = data.get("articles", [])

        # Convert all articles into UI-friendly dicts
        return [_format_article(a) for a in articles_raw]

    except Exception:
        # Catch ANY network or parsing error → fallback
        return _fallback_articles()


# -----------------------------------------------------
# PUBLIC API FUNCTIONS
# These are the functions your NewsUI.py calls.
# -----------------------------------------------------

def get_latest_news(sort_order="desc"):
    """
    Fetch latest World Cup / soccer sports news with strict filtering.
    Returned list goes directly into NewsUI card rendering.
    """

    # List of reliable soccer/sports-focused news outlets
    sports_sources = ",".join([
        "bbc-sport",
        "espn",
        "four-four-two",
        "fox-sports",
        "talksport",
        "marca",
        "as",
        "the-athletic"
    ])

    # Query parameters sent to NewsAPI.org
    params = {
        # Force soccer/World Cup relevant topics only
        "q": "(world cup OR fifa OR soccer OR football OR qualifiers)",
        "sources": sports_sources,
        "language": "en",
        "sortBy": "publishedAt",   # newest first
        "apiKey": NEWS_API_KEY
    }

    # Fetch articles using helper
    articles = _fetch_from_newsapi(params)

    # Sort by timestamp in ascending/descending order
    try:
        articles.sort(
            key=lambda a: datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M"),
            reverse=(sort_order == "desc")
        )
    except:
        # UI will still display articles even if timestamps fail
        pass

    return articles


def search_news(query, sort_order="desc"):
    """
    Search articles by keyword *within* top soccer sources.
    Adds soccer/World Cup context so general news is excluded.
    """

    sports_sources = ",".join([
        "bbc-sport",
        "espn",
        "four-four-two",
        "fox-sports",
        "talksport",
        "marca",
        "as",
        "the-athletic"
    ])

    # Combine user's search with soccer context
    params = {
        "q": f"(world cup OR fifa OR soccer OR football) AND ({query})",
        "sources": sports_sources,
        "language": "en",
        "sortBy": "relevancy",  # most relevant first
        "apiKey": NEWS_API_KEY
    }

    articles = _fetch_from_newsapi(params)

    # Safely sort
    try:
        articles.sort(
            key=lambda a: datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M"),
            reverse=(sort_order == "desc")
        )
    except:
        pass

    return articles


def filter_news(source=None, date=None, sort_order="desc"):
    """
    Filter articles by:
      - source: specific news outlets (e.g., ESPN)
      - date: exact YYYY-MM-DD
    """

    params = {
        "q": "world cup OR soccer",
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY
    }

    # Add source filter only if user selected one
    if source:
        params["sources"] = source

    # Date-based filtering is optional
    if date:
        params["from"] = date
        params["to"] = date

    articles = _fetch_from_newsapi(params)

    # Sort results
    try:
        articles.sort(
            key=lambda a: datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M"),
            reverse=(sort_order == "desc")
        )
    except:
        pass

    return articles


def filter_by_date(date_str, sort_order="desc"):
    """
    Filter articles by exact date (YYYY-MM-DD) while keeping soccer-only filtering.
    """

    sports_sources = ",".join([
        "bbc-sport",
        "espn",
        "four-four-two",
        "fox-sports",
        "talksport",
        "marca",
        "as",
        "the-athletic"
    ])

    params = {
        # Still enforce soccer/World Cup relevance
        "q": "(world cup OR fifa OR soccer OR football)",
        "from": date_str,
        "to": date_str,  # same day range
        "sources": sports_sources,
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY
    }

    articles = _fetch_from_newsapi(params)

    # Sort by date
    try:
        articles.sort(
            key=lambda a: datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M"),
            reverse=(sort_order == "desc")
        )
    except:
        pass

    return articles


def get_trending_news():
    """
    Fetch "most popular" sports headlines.
    Popularity is determined by NewsAPI.org's algorithm.
    """
    params = {
        "q": "world cup OR soccer",
        "language": "en",
        "sortBy": "popularity",  # Trending filter
        "apiKey": NEWS_API_KEY
    }

    articles = _fetch_from_newsapi(params)

    return articles
