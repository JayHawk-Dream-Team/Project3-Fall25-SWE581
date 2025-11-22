import streamlit as st
from datetime import datetime

"""Streamlit Newa UI layer for HomeStand.

This page is similar to the EventsUI except its focused on News and Articles
As a result, the cards on this page have been modified to suit that use case
In particular, the News Cards have a preview image and a hyperlink to the full article
"""

def _render_news_cards(sort_order="desc"):
    """
    Each article links to an external URL.
    """

    """TODO: CONNECT TO REAL BACKEND Instead of using fake data"""
    placeholder_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Mock data
    mock_articles = [
        {
            "title": "Spain Advances to World Cup Semifinals",
            "source": "ESPN",
            "summary": "Spain secures a dramatic victory in extra time, moving on to face France.",
            "image": "https://images.pexels.com/photos/399187/pexels-photo-399187.jpeg",
            "timestamp": "2025-01-13 19:30",
            "url": placeholder_url,
        },
        {
            "title": "Injury Report: Key Striker Out Before Quarterfinals",
            "source": "BBC Sports",
            "summary": "Team medical staff confirm the injury will keep the star out for at least 2 weeks.",
            "image": "https://images.pexels.com/photos/6097714/pexels-photo-6097714.jpeg",
            "timestamp": "2025-01-14 10:15",
            "url": placeholder_url,
        },
        {
            "title": "Top 5 Goals of the Group Stage",
            "source": "ESPN",
            "summary": "Carlos and friends score a lot",
            "image": "https://images.pexels.com/photos/114296/pexels-photo-114296.jpeg",
            "timestamp": "2025-01-10 08:45",
            "url": placeholder_url,
        },
    ]

    # Convert timestamps to real datetime objects
    for a in mock_articles:
        a["dt"] = datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M")

    # Sort handling
    mock_articles = sorted(
        mock_articles,
        key=lambda x: x["dt"],
        reverse=(sort_order == "desc")
    )

    # Render
    for article in mock_articles:

        # Clickable image
        st.markdown(
            f"""
            <a href="{article['url']}" target="_blank">
                <img src="{article['image']}" style="width:100%; border-radius:10px;" />
            </a>
            """,
            unsafe_allow_html=True
        )

        # Clickable title
        st.markdown(f"### [{article['title']}]({article['url']})")

        st.markdown(f"**Source:** {article['source']}")
        st.markdown(f"**Published:** {article['timestamp']}")
        st.write(article["summary"])

        st.divider()


def show_news_page():
    """
    Main UI function for the News Dashboard.
    This is what the main app should call when the user selects "News".
    """

    st.title("Sports & Tournament News")
    st.write("The Hottest News Since Skibbidy Toilet")

    st.subheader("Search")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.text_input(
            "Search headlines",
            placeholder="Type any keyword...",
            key="news_search_input"
        )

    with col2:
        sort_order = st.selectbox(
            "Sort by date",
            ["Descending", "Ascending"],
            key="news_sort_order"
        )

    sort_order = "asc" if sort_order == "Ascending" else "desc"

    st.divider()

    st.subheader("Latest Headlines")
    _render_news_cards(sort_order=sort_order)


if __name__ == "__main__":
    render_news_page()
