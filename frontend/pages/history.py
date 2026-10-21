"""History, archives, and management page for all user assets."""

import streamlit as st
from frontend.api_client import api_client
from frontend.utils.formatting import format_timestamp


def render_history_page():
    st.markdown("## 📜 History & Archives")
    st.caption("Review, inspect, and manage all your historical documents, summaries, and chat threads.")

    tab_sources, tab_summaries, tab_chats = st.tabs(["📁 Ingested Sources", "📝 Generated Summaries", "💬 Chat Threads"])

    # 1. Sources Tab
    with tab_sources:
        try:
            sources = api_client.list_sources()
        except Exception as e:
            st.error(f"Failed to fetch sources: {str(e)}")
            sources = []

        if not sources:
            st.info("No saved sources.")
        else:
            for s in sources:
                with st.expander(f"📄 {s.get('title') or 'Untitled'} ({s.get('source_type')}) - {format_timestamp(s.get('created_at'))}"):
                    st.json(s.get("content_metadata") or {})
                    if st.button("🗑️ Delete Source", key=f"hist_del_src_{s.get('id')}"):
                        api_client.delete_source(s.get("id"))
                        st.toast("Source deleted.")
                        st.rerun()

    # 2. Summaries Tab
    with tab_summaries:
        try:
            summaries = api_client.list_summaries()
        except Exception as e:
            st.error(f"Failed to fetch summaries: {str(e)}")
            summaries = []

        if not summaries:
            st.info("No saved summaries.")
        else:
            for sm in summaries:
                with st.expander(f"📝 {sm.get('title')} ({sm.get('summary_type')}) - {format_timestamp(sm.get('created_at'))}"):
                    st.markdown(sm.get("summary_text", ""))
                    st.caption(f"Model: `{sm.get('model_name')}`")
                    if st.button("🗑️ Delete Summary", key=f"hist_del_sum_{sm.get('id')}"):
                        api_client.delete_summary(sm.get("id"))
                        st.toast("Summary deleted.")
                        st.rerun()

    # 3. Chat Threads Tab
    with tab_chats:
        try:
            conversations = api_client.list_conversations()
        except Exception as e:
            st.error(f"Failed to fetch conversations: {str(e)}")
            conversations = []

        if not conversations:
            st.info("No saved chat threads.")
        else:
            for conv in conversations:
                with st.expander(f"💬 {conv.get('title')} - {format_timestamp(conv.get('created_at'))}"):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button("Open in Chat", key=f"hist_open_conv_{conv.get('id')}"):
                            st.session_state["active_conversation_id"] = conv.get("id")
                            st.session_state["current_page"] = "Chat"
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Delete", key=f"hist_del_conv_{conv.get('id')}"):
                            api_client.delete_conversation(conv.get("id"))
                            st.toast("Conversation deleted.")
                            st.rerun()
