import streamlit as st
from datetime import datetime
from NewsAPI import get_latest_news, search_news, filter_by_date

"""Streamlit News UI layer for HomeStand.

This page is similar to the EventsUI except it's focused on News and Articles.
As a result, the cards have been modified to suit this use case.
News cards have a preview image and hyperlink to the full article.
"""

def _render_news_cards(articles, sort_order="desc"):
    """
    Render a list of articles using the UI format.
    Each article links to an external URL.
    """

    # Parse timestamps into datetime objects so sorting works reliably
    for a in articles:
        try:
            a["dt"] = datetime.strptime(a["timestamp"], "%Y-%m-%d %H:%M")
        except Exception:
            a["dt"] = datetime.now()  # fallback

    # Apply sort
    articles = sorted(
        articles,
        key=lambda x: x["dt"],
        reverse=(sort_order == "desc")
    )

    # Render each article card
    for article in articles:

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
        st.markdown(f"**Preview:** {article['summary']}")


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

    # ---- SEARCH INPUT ----
    with col1:
        st.text_input(
            "Search headlines",
            placeholder="Type any keyword...",
            key="news_search_input"
        )

    # ---- SORT SELECTOR ----
    with col2:
        sort_order = st.selectbox(
            "Sort by date",
            ["Descending", "Ascending"],
            key="news_sort_order"
        )

    with st.expander("Filter by date"):
        filter_date = st.date_input(
            "Select a date (optional)",
            value=None,
            key="news_date_filter"
        )


    sort_order = "asc" if sort_order == "Ascending" else "desc"

    # Divider before content section
    st.divider()

    # Fetch from backend
    query = st.session_state.get("news_search_input", "").strip()

    query = st.session_state.get("news_search_input", "").strip()
    selected_date = st.session_state.get("news_date_filter", None)

    if selected_date:
        # Convert Python date → string 'YYYY-MM-DD'
        date_str = selected_date.strftime("%Y-%m-%d")
    else:
        date_str = None

    # Decide which backend function to use
    if query and date_str:
        articles = search_news(query, sort_order=sort_order, date=date_str)
    elif query:
        articles = search_news(query, sort_order=sort_order)
    elif date_str:
        articles = filter_by_date(date_str, sort_order=sort_order)
    else:
        articles = get_latest_news(sort_order=sort_order)



    # ---- UI Header ----
    st.subheader("Latest Headlines" if not query else f"Search Results for '{query}'")

    # ---- Render cards ----
    if articles:
        _render_news_cards(articles, sort_order=sort_order)
    else:
        st.info("No articles found. Try a different keyword.")


if __name__ == "__main__":
    show_news_page()
