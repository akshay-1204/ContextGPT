"""Sidebar navigation and branding component."""

import streamlit as st
from frontend.utils.session import clear_user_session
from frontend.api_client import api_client


def render_sidebar():
    """Renders the consistent branded ContextGPT sidebar navigation."""
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0 20px 0;">
                <h2 style="color: #6366f1; margin-bottom: 2px;">⚡ ContextGPT</h2>
                <p style="font-size: 0.85rem; color: #888; margin-top: 0;">Understand more. Ask anything.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        authenticated = st.session_state.get("authenticated", False)
        user = st.session_state.get("user")

        if authenticated and user:
            st.markdown(f"**👤 {user.get('name', 'User')}**")
            st.caption(f"{user.get('email', '')}")
            st.divider()

            pages = [
                ("📊 Dashboard", "Dashboard"),
                ("📁 Add / View Sources", "Sources"),
                ("📝 Summarization", "Summaries"),
                ("💬 Ask ContextGPT", "Chat"),
                ("📜 History & Archives", "History"),
            ]

            current_page = st.session_state.get("current_page", "Dashboard")

            for label, page_key in pages:
                btn_type = "primary" if current_page == page_key else "secondary"
                if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=btn_type):
                    st.session_state["current_page"] = page_key
                    st.rerun()

            st.divider()
            if st.button("🚪 Sign Out", key="logout_btn", use_container_width=True):
                api_client.logout()
                clear_user_session()
                st.rerun()
        else:
            auth_pages = [
                ("🔑 Login", "Login"),
                ("✨ Create Account", "Register"),
            ]
            current_page = st.session_state.get("current_page", "Login")
            for label, page_key in auth_pages:
                btn_type = "primary" if current_page == page_key else "secondary"
                if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=btn_type):
                    st.session_state["current_page"] = page_key
                    st.rerun()

        st.markdown("---")
        st.markdown(
            "<div style='font-size: 0.75rem; color: #666; text-align: center;'>"
            "ContextGPT Platform v1.0<br/>RAG & Summarization Engine"
            "</div>",
            unsafe_allow_html=True,
        )
