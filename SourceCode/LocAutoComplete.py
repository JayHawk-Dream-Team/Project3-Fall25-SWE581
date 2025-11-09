import requests

# autocomplete option for the event location
def suggest_location(query: str) -> list:
    if not query:
        return []
    endpoint = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 5,
    }
    headers = {"User-Agent": "streamlit-party-app/1.0"}
    resp = requests.get(endpoint, params=params, headers=headers)
    if resp.status_code != 200:
        return []
    results = resp.json()

    return [r["display_name"] for r in results]
