"""Source ingestion input form component."""

import json
import streamlit as st
from frontend.api_client import api_client


def render_source_input_form(on_success_callback=None):
    """Renders multi-tab input form for adding new knowledge sources."""
    st.markdown("### ➕ Connect a New Knowledge Source")

    tabs = st.tabs(["📄 Document Upload", "🎥 YouTube Video", "🌐 Webpage URL", "🔌 REST API", "🗄️ Database Query"])

    # 1. Document Upload Tab
    with tabs[0]:
        st.caption("Upload documents: PDF, TXT, CSV, Word (.docx), Excel (.xlsx), JSON, XML, or Images.")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "md", "csv", "docx", "xlsx", "json", "xml", "png", "jpg", "jpeg", "webp"],
            key="file_uploader",
        )
        custom_file_title = st.text_input("Custom Title (Optional)", key="file_title_input")

        if st.button("Upload & Index Document", key="btn_upload_file", type="primary"):
            if not uploaded_file:
                st.error("Please select a file to upload.")
            else:
                with st.spinner("Uploading and indexing document content..."):
                    try:
                        file_bytes = uploaded_file.getvalue()
                        source = api_client.upload_file(
                            file_bytes=file_bytes,
                            filename=uploaded_file.name,
                            title=custom_file_title.strip() or None,
                        )
                        st.success(f"Source '{source.get('title')}' successfully ingested and indexed!")
                        if on_success_callback:
                            on_success_callback(source)
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")

    # 2. YouTube Video Tab
    with tabs[1]:
        st.caption("Summarize any YouTube video. Enter the video link to automatically extract the transcript.")
        yt_url = st.text_input(
            "YouTube Video URL",
            placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...",
            key="yt_url_input",
        )
        yt_title = st.text_input("Custom Title (Optional)", key="yt_title_input")

        if st.button("Transcribe & Index YouTube Video", key="btn_fetch_youtube", type="primary"):
            if not yt_url or not ("youtube.com" in yt_url or "youtu.be" in yt_url):
                st.error("Please enter a valid YouTube video URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...).")
            else:
                with st.spinner("Extracting YouTube transcript and indexing for summarization..."):
                    try:
                        source = api_client.create_youtube_source(
                            url=yt_url.strip(),
                            title=yt_title.strip() or None,
                        )
                        st.success(f"YouTube video '{source.get('title')}' successfully transcribed and indexed!")
                        if on_success_callback:
                            on_success_callback(source)
                    except Exception as e:
                        st.error(f"YouTube transcription failed: {str(e)}")

    # 3. Webpage URL Tab
    with tabs[2]:

        st.caption("Extract content from any public HTTP/HTTPS article or documentation page.")
        web_url = st.text_input("Webpage URL", placeholder="https://en.wikipedia.org/wiki/Python_(programming_language)", key="web_url_input")
        web_title = st.text_input("Title (Optional)", key="web_title_input")

        if st.button("Fetch & Index Webpage", key="btn_fetch_webpage", type="primary"):
            if not web_url or not web_url.startswith(("http://", "https://")):
                st.error("Please enter a valid HTTP or HTTPS URL.")
            else:
                with st.spinner("Extracting webpage text with SSRF protection..."):
                    try:
                        source = api_client.create_webpage_source(
                            url=web_url.strip(),
                            title=web_title.strip() or None,
                        )
                        st.success(f"Webpage '{source.get('title')}' successfully indexed!")
                        if on_success_callback:
                            on_success_callback(source)
                    except Exception as e:
                        st.error(f"Extraction failed: {str(e)}")

    # 4. REST API Tab
    with tabs[3]:
        st.caption("Connect an external REST API returning JSON data.")
        api_endpoint = st.text_input("API Endpoint URL", placeholder="https://api.github.com/repos/psf/requests", key="api_url_input")
        api_headers_raw = st.text_area("Optional Headers (JSON format)", placeholder='{"Authorization": "Bearer token"}', key="api_headers_input")
        api_title = st.text_input("Title (Optional)", key="api_title_input")

        if st.button("Query & Index API", key="btn_query_api", type="primary"):
            if not api_endpoint or not api_endpoint.startswith(("http://", "https://")):
                st.error("Please enter a valid API endpoint URL.")
            else:
                headers_dict = None
                if api_headers_raw.strip():
                    try:
                        headers_dict = json.loads(api_headers_raw)
                        if not isinstance(headers_dict, dict):
                            st.error("Headers must be a valid JSON dictionary.")
                            return
                    except Exception:
                        st.error("Invalid JSON format for headers.")
                        return

                with st.spinner("Querying API endpoint securely..."):
                    try:
                        source = api_client.create_api_source(
                            endpoint_url=api_endpoint.strip(),
                            headers=headers_dict,
                            title=api_title.strip() or None,
                        )
                        st.success(f"API Source '{source.get('title')}' successfully indexed!")
                        if on_success_callback:
                            on_success_callback(source)
                    except Exception as e:
                        st.error(f"API extraction failed: {str(e)}")

    # 5. Database Tab
    with tabs[4]:

        st.caption("Execute an authorized read-only SELECT query against PostgreSQL or SQLite.")
        db_uri = st.text_input(
            "Connection URI",
            placeholder="postgresql://user:password@localhost:5432/dbname or sqlite:///sample.db",
            type="password",
            key="db_uri_input",
        )
        db_query = st.text_area("SQL SELECT Query", placeholder="SELECT id, name, email FROM customers LIMIT 100;", key="db_query_input")
        db_title = st.text_input("Source Title (Optional)", key="db_title_input")

        if st.button("Execute & Index Database Rows", key="btn_query_db", type="primary"):
            if not db_uri or not db_query:
                st.error("Connection URI and SQL SELECT query are required.")
            else:
                with st.spinner("Connecting and running read-only query..."):
                    try:
                        source = api_client.create_database_source(
                            connection_string=db_uri.strip(),
                            query=db_query.strip(),
                            title=db_title.strip() or None,
                        )
                        st.success(f"Database Source '{source.get('title')}' successfully indexed!")
                        if on_success_callback:
                            on_success_callback(source)
                    except Exception as e:
                        st.error(f"Database query failed: {str(e)}")
