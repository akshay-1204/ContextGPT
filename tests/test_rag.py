"""Tests for RAG pipeline: chunking, vector retrieval, grounded answers, and multi-user isolation."""

import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.db.models.chunk import DocumentChunk
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.retrieval_service import RetrievalService


def test_chunking_and_metadata_preservation(db_session: Session):
    service = EmbeddingService(db_session)
    long_text = "Python is great.\n\n" * 100
    chunks = service.chunk_text(long_text, chunk_size=200, chunk_overlap=30)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 250


def test_embedding_generation_fallback(db_session: Session):
    service = EmbeddingService(db_session)
    vector = service.generate_embedding("Test document sentence.")
    assert isinstance(vector, list)
    assert len(vector) == 1536
    # Verify non-zero vector
    assert sum(abs(v) for v in vector) > 0


def test_rag_retrieval_and_source_references(client: TestClient, auth_headers: dict):
    # 1. Upload source with specific technical facts
    doc_content = (
        b"In Python, the map() function applies a given function to each item of an iterable "
        b"and returns a map object (an iterator). In contrast, the filter() function constructs "
        b"an iterator from elements of an iterable for which a function returns true. "
        b"Therefore, map transforms items while filter selects items based on a boolean predicate."
    )
    files = {"file": ("python_functions.txt", io.BytesIO(doc_content), "text/plain")}
    upload_res = client.post("/api/v1/sources/upload", headers=auth_headers["headers"], files=files)
    assert upload_res.status_code == 201
    source_id = upload_res.json()["id"]

    # 2. Ask RAG question
    chat_payload = {
        "question": "What is the difference between map() and filter() according to this document?",
        "source_id": source_id,
    }
    chat_res = client.post("/api/v1/chat/ask", headers=auth_headers["headers"], json=chat_payload)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    assert chat_data["is_grounded"] is True
    assert len(chat_data["source_references"]) > 0
    ref = chat_data["source_references"][0]
    assert ref["source_id"] == source_id
    assert "similarity_score" in ref

    # 3. Verify conversation and messages were saved in database
    conv_id = chat_data["conversation_id"]
    conv_res = client.get(f"/api/v1/chat/conversations/{conv_id}", headers=auth_headers["headers"])
    assert conv_res.status_code == 200
    messages = conv_res.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_rag_multi_user_isolation(client: TestClient, auth_headers: dict, second_user_headers: dict):
    # User 1 uploads proprietary data
    secret_text = b"Project X Alpha secret code is 987654321."
    files = {"file": ("secret_x.txt", io.BytesIO(secret_text), "text/plain")}
    src1 = client.post("/api/v1/sources/upload", headers=auth_headers["headers"], files=files)
    src1_id = src1.json()["id"]

    # User 2 asks about Project X Alpha
    chat_payload = {
        "question": "What is the secret code for Project X Alpha?",
    }
    intruder_res = client.post("/api/v1/chat/ask", headers=second_user_headers["headers"], json=chat_payload)
    assert intruder_res.status_code == 200
    intruder_data = intruder_res.json()

    # User 2 should find NO chunks and receive honest answer about insufficient information
    assert intruder_data["is_grounded"] is False
    assert len(intruder_data["source_references"]) == 0
    assert "do not contain sufficient information" in intruder_data["answer"].lower()
