"""Centralized API client for communicating with ContextGPT backend."""

import os
from typing import Optional, Dict, Any, List
import requests
import streamlit as st


class APIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("API_BASE_URL") or "http://localhost:8000").rstrip("/")

    def _get_headers(self, requires_auth: bool = True) -> Dict[str, str]:
        headers = {}
        if requires_auth:
            token = st.session_state.get("access_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        requires_auth: bool = True,
        **kwargs
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = self._get_headers(requires_auth)
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        response = requests.request(method, url, headers=headers, timeout=60, **kwargs)

        # Handle token expiry and auto-refresh
        if response.status_code == 401 and requires_auth and st.session_state.get("refresh_token"):
            if self._attempt_token_refresh():
                headers = self._get_headers(requires_auth)
                response = requests.request(method, url, headers=headers, timeout=60, **kwargs)

        return response

    def _attempt_token_refresh(self) -> bool:
        refresh_token = st.session_state.get("refresh_token")
        if not refresh_token:
            return False
        try:
            res = requests.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=10,
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state["access_token"] = data["access_token"]
                st.session_state["refresh_token"] = data["refresh_token"]
                return True
        except Exception:
            pass
        return False

    # Health
    def get_health(self) -> Dict[str, Any]:
        res = self._request("GET", "/health", requires_auth=False)
        return res.json() if res.status_code == 200 else {}

    # Auth
    def register(self, name: str, email: str, password: str, password_confirm: str) -> Dict[str, Any]:
        res = self._request(
            "POST",
            "/api/v1/auth/register",
            requires_auth=False,
            json={
                "name": name,
                "email": email,
                "password": password,
                "password_confirm": password_confirm,
            },
        )
        if res.status_code not in (200, 201):
            detail = res.json().get("detail", "Registration failed.")
            raise Exception(detail)
        return res.json()

    def login(self, email: str, password: str) -> Dict[str, Any]:
        res = self._request(
            "POST",
            "/api/v1/auth/login",
            requires_auth=False,
            json={"email": email, "password": password},
        )
        if res.status_code != 200:
            detail = res.json().get("detail", "Login failed. Check your credentials.")
            raise Exception(detail)
        return res.json()

    def get_me(self) -> Dict[str, Any]:
        res = self._request("GET", "/api/v1/auth/me", requires_auth=True)
        if res.status_code != 200:
            raise Exception("Failed to retrieve profile.")
        return res.json()

    def logout(self) -> bool:
        refresh_token = st.session_state.get("refresh_token")
        if refresh_token:
            try:
                self._request("POST", "/api/v1/auth/logout", requires_auth=False, json={"refresh_token": refresh_token})
            except Exception:
                pass
        return True

    # Sources
    def upload_file(self, file_bytes: bytes, filename: str, title: Optional[str] = None) -> Dict[str, Any]:
        files = {"file": (filename, file_bytes)}
        data = {"title": title} if title else {}
        res = self._request("POST", "/api/v1/sources/upload", requires_auth=True, files=files, data=data)
        if res.status_code not in (200, 201):
            raise Exception(res.json().get("detail", "File upload failed."))
        return res.json()

    def create_webpage_source(self, url: str, title: Optional[str] = None) -> Dict[str, Any]:
        res = self._request(
            "POST",
            "/api/v1/sources/webpage",
            requires_auth=True,
            json={"url": url, "title": title},
        )
        if res.status_code not in (200, 201):
            raise Exception(res.json().get("detail", "Webpage ingestion failed."))
        return res.json()

    def create_api_source(self, endpoint_url: str, headers: Optional[Dict[str, str]] = None, title: Optional[str] = None) -> Dict[str, Any]:
        res = self._request(
            "POST",
            "/api/v1/sources/api",
            requires_auth=True,
            json={"endpoint_url": endpoint_url, "headers": headers, "title": title},
        )
        if res.status_code not in (200, 201):
            raise Exception(res.json().get("detail", "API source extraction failed."))
        return res.json()

    def create_database_source(self, connection_string: str, query: str, title: Optional[str] = None) -> Dict[str, Any]:
        res = self._request(
            "POST",
            "/api/v1/sources/database",
            requires_auth=True,
            json={"connection_string": connection_string, "query": query, "title": title},
        )
        if res.status_code not in (200, 201):
            raise Exception(res.json().get("detail", "Database extraction failed."))
        return res.json()

    def create_youtube_source(self, url: str, title: Optional[str] = None) -> Dict[str, Any]:
        res = self._request(
            "POST",
            "/api/v1/sources/youtube",
            requires_auth=True,
            json={"url": url, "title": title},
        )
        if res.status_code not in (200, 201):
            raise Exception(res.json().get("detail", "YouTube video ingestion failed."))
        return res.json()


    def list_sources(self) -> List[Dict[str, Any]]:
        res = self._request("GET", "/api/v1/sources", requires_auth=True)
        if res.status_code != 200:
            return []
        return res.json()

    def get_source(self, source_id: int) -> Dict[str, Any]:
        res = self._request("GET", f"/api/v1/sources/{source_id}", requires_auth=True)
        if res.status_code != 200:
            raise Exception("Source not found.")
        return res.json()

    def delete_source(self, source_id: int) -> bool:
        res = self._request("DELETE", f"/api/v1/sources/{source_id}", requires_auth=True)
        return res.status_code == 200

    # Summaries
    def create_summary(
        self,
        source_id: int,
        summary_type: str = "short",
        custom_instructions: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "source_id": source_id,
            "summary_type": summary_type,
            "custom_instructions": custom_instructions,
            "title": title,
        }
        res = self._request("POST", "/api/v1/summaries", requires_auth=True, json=payload)
        if res.status_code not in (200, 201):
            raise Exception(res.json().get("detail", "Summarization failed."))
        return res.json()

    def list_summaries(self) -> List[Dict[str, Any]]:
        res = self._request("GET", "/api/v1/summaries", requires_auth=True)
        if res.status_code != 200:
            return []
        return res.json()

    def get_summary(self, summary_id: int) -> Dict[str, Any]:
        res = self._request("GET", f"/api/v1/summaries/{summary_id}", requires_auth=True)
        if res.status_code != 200:
            raise Exception("Summary not found.")
        return res.json()

    def delete_summary(self, summary_id: int) -> bool:
        res = self._request("DELETE", f"/api/v1/summaries/{summary_id}", requires_auth=True)
        return res.status_code == 200

    # Chat & RAG
    def ask_question(
        self,
        question: str,
        conversation_id: Optional[int] = None,
        source_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload = {
            "question": question,
            "conversation_id": conversation_id,
            "source_id": source_id,
        }
        res = self._request("POST", "/api/v1/chat/ask", requires_auth=True, json=payload)
        if res.status_code != 200:
            raise Exception(res.json().get("detail", "Error answering question."))
        return res.json()

    def list_conversations(self) -> List[Dict[str, Any]]:
        res = self._request("GET", "/api/v1/chat/conversations", requires_auth=True)
        if res.status_code != 200:
            return []
        return res.json()

    def get_conversation(self, conversation_id: int) -> Dict[str, Any]:
        res = self._request("GET", f"/api/v1/chat/conversations/{conversation_id}", requires_auth=True)
        if res.status_code != 200:
            raise Exception("Conversation not found.")
        return res.json()

    def delete_conversation(self, conversation_id: int) -> bool:
        res = self._request("DELETE", f"/api/v1/chat/conversations/{conversation_id}", requires_auth=True)
        return res.status_code == 200


api_client = APIClient()
