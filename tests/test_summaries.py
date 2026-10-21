"""Tests for document summarization workflows and ownership rules."""

import io
from fastapi.testclient import TestClient


def test_summarization_workflow(client: TestClient, auth_headers: dict):
    # Ingest document
    content = (
        b"Machine learning is a field of study in artificial intelligence concerned with the "
        b"development and study of statistical algorithms that can learn from data and generalize "
        b"to unseen data, thus performing tasks without explicit instructions."
    )
    files = {"file": ("ml_overview.txt", io.BytesIO(content), "text/plain")}
    src_res = client.post("/api/v1/sources/upload", headers=auth_headers["headers"], files=files)
    source_id = src_res.json()["id"]

    # Generate summary
    sum_payload = {
        "source_id": source_id,
        "summary_type": "short",
        "title": "ML Executive Summary",
    }
    res = client.post("/api/v1/summaries", headers=auth_headers["headers"], json=sum_payload)
    assert res.status_code == 201
    summary = res.json()
    assert summary["title"] == "ML Executive Summary"
    assert summary["summary_type"] == "short"
    assert len(summary["summary_text"]) > 0

    # List summaries
    list_res = client.get("/api/v1/summaries", headers=auth_headers["headers"])
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_summary_ownership_isolation(client: TestClient, auth_headers: dict, second_user_headers: dict):
    # User 1 uploads document
    files = {"file": ("doc.txt", io.BytesIO(b"Confidential summary material."), "text/plain")}
    src_res = client.post("/api/v1/sources/upload", headers=auth_headers["headers"], files=files)
    source_id = src_res.json()["id"]

    # User 2 attempts to summarize User 1's source -> 400 (not allowed)
    sum_payload = {"source_id": source_id, "summary_type": "short"}
    forbidden_res = client.post("/api/v1/summaries", headers=second_user_headers["headers"], json=sum_payload)
    assert forbidden_res.status_code == 400
    assert "not found or you do not have permission" in forbidden_res.json()["detail"].lower()


def test_source_type_specific_prompts():
    """Verify that every loader type has a dedicated tailored prompt."""
    from backend.app.prompts.summarization import get_source_type_prompt, get_summarization_prompt
    from backend.app.loaders.loader_registry import list_supported_types

    supported_types = list_supported_types()
    assert len(supported_types) > 0

    for st in supported_types:
        prompt = get_source_type_prompt(st)
        assert prompt is not None
        assert len(prompt) > 50
        # Make sure it's not the generic fallback
        assert "document analyst" not in prompt.lower() or st in ["txt", "text", "md"]

    # Verify specific keywords for key loaders
    assert "pdf document summarizer" in get_source_type_prompt("pdf").lower()
    assert "api response data analyst" in get_source_type_prompt("api").lower()
    assert "universal data summarizer" in get_source_type_prompt("url").lower()
    assert "stock market data analyst" in get_source_type_prompt("stock").lower()
    assert "tabular data analyst" in get_source_type_prompt("csv").lower()
    assert "database query results analyst" in get_source_type_prompt("database").lower()
    assert "video transcript summarizer" in get_source_type_prompt("youtube").lower()
    assert "web content summarizer" in get_source_type_prompt("webpage").lower()

    # Verify full prompt builder includes source type persona
    pdf_full = get_summarization_prompt(summary_type="detailed", source_type="pdf")
    assert "pdf document summarizer" in pdf_full.lower()
    assert "exhaustive, in-depth analytical summary" in pdf_full.lower()

    api_full = get_summarization_prompt(summary_type="bullet_points", source_type="api")
    assert "api response data analyst" in api_full.lower()
    assert "bullet points" in api_full.lower()

    # Verify fallback for unknown source type
    unknown = get_source_type_prompt("unknown_type_xyz")
    assert "expert ai document analyst" in unknown.lower()

