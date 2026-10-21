"""Summarization page with multiple styles and custom guidelines."""

import streamlit as st
from frontend.api_client import api_client
from frontend.components.summary_view import render_summary_card


def render_summaries_page():
    st.markdown("## 📝 Document Summarization")
    st.caption("Generate high-precision executive summaries, bullet points, or customized analyses.")

    # 1. Fetch available sources
    try:
        sources = api_client.list_sources()
        ready_sources = [s for s in sources if s.get("processing_status") == "completed"]
    except Exception as e:
        st.error(f"Error fetching sources: {str(e)}")
        ready_sources = []

    if not ready_sources:
        st.warning("You have no ready sources to summarize. Please ingest a source first.")
        if st.button("Go to Add Sources", type="primary"):
            st.session_state["current_page"] = "Sources"
            st.rerun()
        return

    # Source Selection
    source_options = {s["id"]: f"{s.get('title') or 'Untitled'} ({s.get('source_type')})" for s in ready_sources}
    default_source_id = st.session_state.get("selected_source_id")
    default_index = 0
    source_id_list = list(source_options.keys())
    if default_source_id in source_id_list:
        default_index = source_id_list.index(default_source_id)

    with st.container(border=True):
        st.markdown("### ⚙️ Summarization Options")

        col1, col2 = st.columns([3, 2])
        with col1:
            selected_source_id = st.selectbox(
                "Select Knowledge Source",
                options=source_id_list,
                format_func=lambda sid: source_options.get(sid, f"Source #{sid}"),
                index=default_index,
                key="summary_source_selector",
            )
        with col2:
            summary_style = st.selectbox(
                "Summary Style",
                options=["short", "detailed", "bullet_points", "key_takeaways", "custom"],
                format_func=lambda x: {
                    "short": "Short Executive Summary (1-2 paragraphs)",
                    "detailed": "Detailed & Exhaustive Analysis",
                    "bullet_points": "Structured Bullet Points",
                    "key_takeaways": "Key Actionable Takeaways",
                    "custom": "Custom Instructions",
                }.get(x, x),
                key="summary_style_selector",
            )

        custom_instructions = None
        if summary_style == "custom":
            custom_instructions = st.text_area(
                "Custom Guidelines & Focus Areas",
                placeholder="e.g. Focus on financial metrics, risk factors, and deadlines mentioned in Q3.",
                key="custom_guidelines_input",
            )

        custom_title = st.text_input("Summary Title (Optional)", key="summary_title_input")

        if st.button("🚀 Generate Summary", type="primary", use_container_width=True, key="btn_run_summary"):
            with st.spinner("Analyzing document and synthesizing summary..."):
                try:
                    new_summary = api_client.create_summary(
                        source_id=selected_source_id,
                        summary_type=summary_style,
                        custom_instructions=custom_instructions,
                        title=custom_title.strip() or None,
                    )
                    st.success("Summary generated successfully!")
                    st.session_state["last_generated_summary"] = new_summary
                except Exception as e:
                    st.error(f"Failed to generate summary: {str(e)}")

    # Display Last Generated Summary
    last_summary = st.session_state.get("last_generated_summary")
    if last_summary:
        st.markdown("### 🌟 Latest Generated Summary")
        render_summary_card(last_summary)

    st.markdown("---")

    # Saved Summaries
    st.markdown("### 📚 Saved Summaries for this User")
    try:
        all_summaries = api_client.list_summaries()
    except Exception as e:
        all_summaries = []

    if not all_summaries:
        st.info("No saved summaries yet.")
    else:
        for sm in all_summaries:
            def on_delete(sid):
                api_client.delete_summary(sid)
                st.rerun()

            render_summary_card(sm, allow_delete=True, on_delete=on_delete)
