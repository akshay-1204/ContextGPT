"""ContextGPT Streamlit Application Main Entrypoint."""

import os
import sys

# Ensure the project root directory is in sys.path so 'frontend...' imports resolve
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

# 1. Page Configuration
st.set_page_config(
    page_title="ContextGPT - Understand more. Ask anything.",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Rich Modern Custom CSS Styling
st.markdown(
    """
    <style>
    /* Global Typography & Tone */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Primary Action Buttons */
    button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    button[kind="primary"]:hover {
        opacity: 0.92 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35) !important;
    }

    /* Card Containers */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border: 1px solid rgba(120, 120, 128, 0.2) !important;
        transition: border-color 0.2s ease;
    }

    /* Badges & Metrics */
    [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        color: #6366f1 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(120, 120, 128, 0.15) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Session State Initialization
from frontend.utils.session import init_session_state
init_session_state()

# 4. Import Components & Pages
from frontend.components.navigation import render_sidebar
from frontend.pages.login import render_login_page
from frontend.pages.register import render_register_page
from frontend.pages.dashboard import render_dashboard_page
from frontend.pages.sources import render_sources_page
from frontend.pages.summaries import render_summaries_page
from frontend.pages.chat import render_chat_page
from frontend.pages.history import render_history_page

# 5. Render Sidebar Navigation
render_sidebar()

# 6. Page Routing
authenticated = st.session_state.get("authenticated", False)
current_page = st.session_state.get("current_page", "Dashboard" if authenticated else "Login")

if not authenticated:
    if current_page == "Register":
        render_register_page()
    else:
        render_login_page()
else:
    if current_page == "Dashboard":
        render_dashboard_page()
    elif current_page == "Sources":
        render_sources_page()
    elif current_page == "Summaries":
        render_summaries_page()
    elif current_page == "Chat":
        render_chat_page()
    elif current_page == "History":
        render_history_page()
    else:
        render_dashboard_page()
