"""Streamlit dashboard entry point.

Run with: streamlit run src/graphhansard/dashboard/app.py

See SRD §9 (Layer 3 — The Map) for specification.
"""

from __future__ import annotations


def main():
    """Launch the GraphHansard interactive dashboard."""
    # TODO: Implement dashboard — see Issues #15 through #19
    try:
        import streamlit as st
    except ImportError:
        print("Streamlit is required. Install with: pip install -e '.[dashboard]'")
        return

    st.set_page_config(
        page_title="GraphHansard — Bahamian Parliamentary Network",
        page_icon="🏛️",
        layout="wide",
    )

    st.title("GraphHansard")
    st.subheader("Bahamian House of Assembly — Political Interaction Network")

    st.info(
        "Dashboard is under construction. "
        "See the [project roadmap](https://github.com/caribdigital/graphhansard) "
        "for progress updates."
    )


if __name__ == "__main__":
    main()
