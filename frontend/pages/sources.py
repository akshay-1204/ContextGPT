"""Sources management and ingestion page."""

import streamlit as st
from frontend.api_client import api_client
from frontend.components.source_input import render_source_input_form
from frontend.utils.formatting import format_timestamp


def render_sources_page():
    st.markdown("## 📁 Knowledge Sources")
    st.caption("Manage all documents, URLs, APIs, and databases indexed into ContextGPT.")

    # 1. Ingestion Form Expander
    with st.expander("➕ Ingest a New Source (PDF, 🎥 YouTube, Webpage, API, Database)", expanded=True):

        def on_uploaded(new_src):
            st.rerun()

        render_source_input_form(on_success_callback=on_uploaded)

    st.markdown("---")

    # 2. Existing Sources Table / Cards
    st.markdown("### 📚 Your Ingested Sources")
    try:
        sources = api_client.list_sources()
    except Exception as e:
        st.error(f"Failed to fetch sources: {str(e)}")
        sources = []

    if not sources:
        st.info("No sources added yet. Use the expander above to add your first document or webpage.")
        return

    for src in sources:
        with st.container(border=True):
            col_info, col_actions = st.columns([4, 2])

            with col_info:
                status = src.get("processing_status", "pending")
                badge = "🟢 Ready" if status == "completed" else "🔴 Failed" if status == "failed" else "🟡 Processing"

                st.markdown(f"#### {src.get('title') or 'Untitled Source'}  `{badge}`")
                st.caption(
                    f"**Type:** `{src.get('source_type')}` | "
                    f"**Added:** {format_timestamp(src.get('created_at'))} | "
                    f"**Reference:** `{src.get('source_reference')[:60]}`"
                )

                if status == "failed" and src.get("error_message"):
                    st.error(f"Error: {src.get('error_message')}")

                meta = src.get("content_metadata") or {}
                if meta.get("char_count"):
                    st.caption(f"📊 Extracted Content: {meta.get('char_count'):,} characters")

            with col_actions:
                st.write("")
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if status == "completed":
                        if st.button("📝 Summarize", key=f"sum_src_{src.get('id')}", use_container_width=True):
                            st.session_state["selected_source_id"] = src.get("id")
                            st.session_state["current_page"] = "Summaries"
                            st.rerun()

                with btn_c2:
                    if status == "completed":
                        if st.button("💬 Ask RAG", key=f"chat_src_{src.get('id')}", use_container_width=True):
                            st.session_state["selected_source_id"] = src.get("id")
                            st.session_state["current_page"] = "Chat"
                            st.rerun()

                if st.button("🗑️ Delete", key=f"del_src_{src.get('id')}", type="secondary", use_container_width=True):
                    try:
                        api_client.delete_source(src.get("id"))
                        st.toast(f"Source #{src.get('id')} deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete source: {str(e)}")
