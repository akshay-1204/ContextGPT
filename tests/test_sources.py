"""Tests for Source ingestion, loaders, SSRF prevention, and access ownership."""

import io
from fastapi.testclient import TestClient


def test_txt_file_upload_and_extraction(client: TestClient, auth_headers: dict):
    file_content = b"Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability."
    files = {"file": ("python_intro.txt", io.BytesIO(file_content), "text/plain")}
    data = {"title": "Python Overview"}

    response = client.post("/api/v1/sources/upload", headers=auth_headers["headers"], files=files, data=data)
    assert response.status_code == 201
    source_data = response.json()
    assert source_data["title"] == "Python Overview"
    assert source_data["source_type"] == "txt"
    assert source_data["processing_status"] == "completed"

    # List sources
    list_res = client.get("/api/v1/sources", headers=auth_headers["headers"])
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_ssrf_protection_blocks_localhost(client: TestClient, auth_headers: dict):
    payload = {
        "url": "http://127.0.0.1:8000/api/v1/private-data",
        "title": "Malicious Webpage",
    }
    response = client.post("/api/v1/sources/webpage", headers=auth_headers["headers"], json=payload)
    assert response.status_code == 201
    data = response.json()
    # Processing status should be failed due to SSRF validator
    assert data["processing_status"] == "failed"
    assert "blocked" in data["error_message"].lower() or "private" in data["error_message"].lower()


def test_source_ownership_isolation(client: TestClient, auth_headers: dict, second_user_headers: dict):
    # User 1 creates source
    file_content = b"Confidential business data strictly for Alice."
    files = {"file": ("alice_secrets.txt", io.BytesIO(file_content), "text/plain")}
    res = client.post("/api/v1/sources/upload", headers=auth_headers["headers"], files=files)
    source_id = res.json()["id"]

    # User 2 attempts to fetch User 1's source -> 404
    forbidden_get = client.get(f"/api/v1/sources/{source_id}", headers=second_user_headers["headers"])
    assert forbidden_get.status_code == 404

    # User 2 attempts to delete User 1's source -> 404
    forbidden_del = client.delete(f"/api/v1/sources/{source_id}", headers=second_user_headers["headers"])
    assert forbidden_del.status_code == 404

    # User 1 can delete their own source
    owner_del = client.delete(f"/api/v1/sources/{source_id}", headers=auth_headers["headers"])
    assert owner_del.status_code == 200


def test_csv_file_upload(client: TestClient, auth_headers: dict):
    csv_data = b"id,name,role\n1,Alice,Engineer\n2,Bob,Architect\n"
    files = {"file": ("team.csv", io.BytesIO(csv_data), "text/csv")}
    res = client.post("/api/v1/sources/upload", headers=auth_headers["headers"], files=files)
    assert res.status_code == 201
    assert res.json()["source_type"] == "csv"
    assert res.json()["processing_status"] == "completed"
