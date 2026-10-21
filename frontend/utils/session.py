"""Session state management for ContextGPT Streamlit frontend."""

import streamlit as st


def init_session_state():
    """Initializes Streamlit session state variables with default values."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "refresh_token" not in st.session_state:
        st.session_state["refresh_token"] = None
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Dashboard" if st.session_state["authenticated"] else "Login"
    if "selected_source_id" not in st.session_state:
        st.session_state["selected_source_id"] = None
    if "active_conversation_id" not in st.session_state:
        st.session_state["active_conversation_id"] = None


def set_user_session(user_data: dict, tokens: dict):
    """Sets authenticated session state upon login/registration."""
    st.session_state["authenticated"] = True
    st.session_state["user"] = user_data
    st.session_state["access_token"] = tokens.get("access_token")
    st.session_state["refresh_token"] = tokens.get("refresh_token")
    st.session_state["current_page"] = "Dashboard"


def clear_user_session():
    """Clears authentication session upon logout."""
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.session_state["access_token"] = None
    st.session_state["refresh_token"] = None
    st.session_state["current_page"] = "Login"
    st.session_state["selected_source_id"] = None
    st.session_state["active_conversation_id"] = None
