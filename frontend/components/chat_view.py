"""Chat conversation view component with citation display."""

import streamlit as st
from frontend.utils.formatting import format_timestamp


def render_chat_messages(messages: list):
    """Renders user questions and assistant answers with grounded citation cards."""
    if not messages:
        st.info("No messages in this conversation yet. Ask a question below to start exploring your documents!")
        return

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        citations = msg.get("source_references") or []

        if role == "user":
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="⚡"):
                st.markdown(content)
                if citations:
                    with st.expander(f"📚 Verified Sources & Citations ({len(citations)} references)"):
                        for cit in citations:
                            st.markdown(
                                f"**{cit.get('citation_label', 'Source')}** — *{cit.get('source_title', 'Document')}* "
                                f"(Section {cit.get('chunk_index', 0) + 1}, Relevance: {cit.get('similarity_score', 0):.2f})"
                            )
                            if cit.get("source_reference"):
                                st.caption(f"Reference: `{cit.get('source_reference')}`")
                            st.divider()
