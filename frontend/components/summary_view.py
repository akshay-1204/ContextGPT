"""Summary presentation component."""

import streamlit as st
from frontend.utils.formatting import format_timestamp


def render_summary_card(summary: dict, allow_delete: bool = False, on_delete=None):
    """Renders a beautifully formatted summary card with metadata tags and copy action."""
    with st.container(border=True):
        st.subheader(summary.get("title") or "Document Summary")

        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            st.caption(f"**Style:** {summary.get('summary_type', 'short').capitalize()}")
        with col2:
            st.caption(f"**Model:** {summary.get('model_name', 'default')}")
        with col3:
            st.caption(f"**Created:** {format_timestamp(summary.get('created_at'))}")

        st.markdown(summary.get("summary_text", ""))

        usage = summary.get("token_usage") or {}
        if usage.get("total_tokens"):
            st.caption(f"🪙 Tokens: {usage.get('total_tokens')} (Prompt: {usage.get('prompt_tokens')}, Completion: {usage.get('completion_tokens')})")

        if allow_delete and on_delete:
            if st.button("🗑️ Delete Summary", key=f"del_sum_{summary.get('id')}"):
                on_delete(summary.get("id"))
