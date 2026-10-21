"""Ask ContextGPT chat and RAG interaction page."""

import streamlit as st
from frontend.api_client import api_client
from frontend.components.chat_view import render_chat_messages


def render_chat_page():
    st.markdown("## 💬 Ask ContextGPT")
    st.caption("Ask questions grounded strictly in your verified source documents using RAG.")

    # Fetch sources and conversations
    try:
        sources = api_client.list_sources()
        ready_sources = [s for s in sources if s.get("processing_status") == "completed"]
        conversations = api_client.list_conversations()
    except Exception as e:
        st.error(f"Failed to load chat context: {str(e)}")
        ready_sources, conversations = [], []

    # Controls row: Conversation Selector + Source Filter Scope
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([3, 3, 2])

    with ctrl_col1:
        conv_options = {0: "➕ Start New Conversation"}
        for c in conversations:
            conv_options[c["id"]] = f"{c.get('title') or 'Conversation'} (#{c['id']})"

        active_conv_id = st.session_state.get("active_conversation_id") or 0
        selected_conv_id = st.selectbox(
            "Active Conversation",
            options=list(conv_options.keys()),
            format_func=lambda cid: conv_options.get(cid, f"Conversation #{cid}"),
            index=list(conv_options.keys()).index(active_conv_id) if active_conv_id in conv_options else 0,
            key="conv_selector",
        )
        if selected_conv_id != active_conv_id:
            st.session_state["active_conversation_id"] = selected_conv_id if selected_conv_id != 0 else None
            st.rerun()

    with ctrl_col2:
        src_filter_options = {0: "🌐 Search All Indexed Sources"}
        for s in ready_sources:
            src_filter_options[s["id"]] = f"{s.get('title') or 'Untitled'} ({s.get('source_type')})"

        default_src_id = st.session_state.get("selected_source_id") or 0
        selected_src_filter = st.selectbox(
            "Filter Knowledge Scope",
            options=list(src_filter_options.keys()),
            format_func=lambda sid: src_filter_options.get(sid, f"Source #{sid}"),
            index=list(src_filter_options.keys()).index(default_src_id) if default_src_id in src_filter_options else 0,
            key="chat_source_filter",
        )

    with ctrl_col3:
        st.write("")
        st.write("")
        if st.button("➕ New Thread", key="btn_new_thread", use_container_width=True):
            st.session_state["active_conversation_id"] = None
            st.rerun()

    st.divider()

    # Load and display conversation messages
    current_conv = None
    messages = []
    if st.session_state.get("active_conversation_id"):
        try:
            current_conv = api_client.get_conversation(st.session_state["active_conversation_id"])
            messages = current_conv.get("messages", [])
        except Exception as e:
            st.warning(f"Could not load conversation messages: {str(e)}")

    render_chat_messages(messages)

    # Question Input
    user_question = st.chat_input("Ask a question about your indexed documents...", key="chat_user_question")
    if user_question:
        if not ready_sources:
            st.warning("You have no indexed sources yet. Please add a document or webpage first so ContextGPT can ground answers.")
        else:
            with st.spinner("Retrieving relevant context and generating grounded answer..."):
                try:
                    scoped_source = selected_src_filter if selected_src_filter != 0 else None
                    active_cid = st.session_state.get("active_conversation_id")

                    response_data = api_client.ask_question(
                        question=user_question,
                        conversation_id=active_cid,
                        source_id=scoped_source,
                    )

                    # Update active conversation id
                    st.session_state["active_conversation_id"] = response_data.get("conversation_id")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error answering question: {str(e)}")
