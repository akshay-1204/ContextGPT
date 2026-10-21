"""Dashboard overview page with live statistics and recent activity."""

import streamlit as st
from frontend.api_client import api_client
from frontend.utils.formatting import format_timestamp


def render_dashboard_page():
    user = st.session_state.get("user") or {}
    st.markdown(f"## 👋 Welcome back, {user.get('name', 'Analyst')}!")
    st.caption("Here is your ContextGPT knowledge graph and activity overview.")

    # Fetch live data from backend
    with st.spinner("Loading metrics..."):
        try:
            sources = api_client.list_sources()
            summaries = api_client.list_summaries()
            conversations = api_client.list_conversations()
        except Exception as e:
            st.error(f"Failed to load metrics from backend: {str(e)}")
            sources, summaries, conversations = [], [], []

    # Real Statistics Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="📚 Total Sources", value=len(sources))
    with col2:
        completed_sources = sum(1 for s in sources if s.get("processing_status") == "completed")
        st.metric(label="✅ Indexed Sources", value=completed_sources)
    with col3:
        st.metric(label="📝 Summaries Generated", value=len(summaries))
    with col4:
        st.metric(label="💬 Active Conversations", value=len(conversations))

    st.markdown("---")

    # Quick Actions
    st.markdown("### ⚡ Quick Actions")
    qcol1, qcol2, qcol3 = st.columns(3)
    with qcol1:
        with st.container(border=True):
            st.markdown("#### 📁 Add Knowledge Source")
            st.caption("Upload PDFs, YouTube videos, web articles, APIs, or databases.")

            if st.button("Add Sources", key="dash_btn_sources", use_container_width=True, type="primary"):
                st.session_state["current_page"] = "Sources"
                st.rerun()

    with qcol2:
        with st.container(border=True):
            st.markdown("#### 📝 Generate Summary")
            st.caption("Create executive, detailed, or custom bulleted summaries.")
            if st.button("Summarize", key="dash_btn_summaries", use_container_width=True):
                st.session_state["current_page"] = "Summaries"
                st.rerun()

    with qcol3:
        with st.container(border=True):
            st.markdown("#### 💬 Ask ContextGPT")
            st.caption("Query your knowledge base with citation-grounded RAG.")
            if st.button("Open Chat", key="dash_btn_chat", use_container_width=True):
                st.session_state["current_page"] = "Chat"
                st.rerun()

    st.markdown("---")

    # Recent Activity (2-column layout)
    act_col1, act_col2 = st.columns(2)

    with act_col1:
        st.markdown("### 📄 Recent Knowledge Sources")
        if not sources:
            st.info("No sources uploaded yet. Click 'Add Sources' above to connect your first document or webpage.")
        else:
            for src in sources[:5]:
                status_icon = "🟢" if src.get("processing_status") == "completed" else "🔴" if src.get("processing_status") == "failed" else "🟡"
                with st.container(border=True):
                    st.markdown(f"**{status_icon} {src.get('title', 'Untitled')}**")
                    st.caption(f"Type: `{src.get('source_type')}` • Added: {format_timestamp(src.get('created_at'))}")

    with act_col2:
        st.markdown("### 📝 Recent Summaries")
        if not summaries:
            st.info("No summaries generated yet. Ingest a source and create your first summary.")
        else:
            for sm in summaries[:5]:
                with st.container(border=True):
                    st.markdown(f"**{sm.get('title', 'Summary')}**")
                    st.caption(f"Style: `{sm.get('summary_type')}` • Created: {format_timestamp(sm.get('created_at'))}")
                    preview = sm.get("summary_text", "")
                    if len(preview) > 120:
                        preview = preview[:120] + "..."
                    st.markdown(f"> {preview}")
