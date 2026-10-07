import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import init_db

init_db()
client = TestClient(app)

def test_list_users_includes_default():
    """Verify that user listing endpoint returns the seeded default user."""
    res = client.get("/api/v1/users")
    assert res.status_code == 200
    users = res.json()
    assert isinstance(users, list)
    assert any(u["username"] == "default" for u in users)

def test_create_and_fetch_user():
    """Verify creating a new user profile and retrieving user details."""
    payload = {
        "username": "qa_analyst_1",
        "display_name": "QA Lead Analyst",
        "email": "qa1@bilangual.ai"
    }
    create_res = client.post("/api/v1/users", json=payload)
    assert create_res.status_code == 200
    data = create_res.json()
    assert data["username"] == "qa_analyst_1"
    assert data["display_name"] == "QA Lead Analyst"

    # Fetch user detail
    detail_res = client.get("/api/v1/users/qa_analyst_1")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["username"] == "qa_analyst_1"
    assert detail["display_name"] == "QA Lead Analyst"

def test_user_specific_translation_and_history():
    """Verify translations logged with a username are filtered correctly by user in history."""
    username = "agent_sarah"
    
    # Pre-create user
    client.post("/api/v1/users", json={"username": username, "display_name": "Sarah Connor"})

    # Translate with this user
    translate_res = client.post("/api/v1/translate", json={
        "text": "Card was swallowed by the ATM machine.",
        "source_lang": "en",
        "target_lang": "ur",
        "session_id": "sess_sarah_101",
        "username": username
    })
    assert translate_res.status_code == 200
    tr_data = translate_res.json()
    assert tr_data["username"] == username

    # Fetch user-specific history
    history_res = client.get(f"/api/v1/history?username={username}")
    assert history_res.status_code == 200
    logs = history_res.json()
    assert len(logs) > 0
    assert all(l["username"] == username for l in logs)
    assert "swallowed" in logs[0]["source_text"]

def test_user_history_isolation():
    """Verify history queries for user A do not leak logs from user B."""
    user_a = "user_alpha"
    user_b = "user_beta"

    # Create both users
    client.post("/api/v1/users", json={"username": user_a})
    client.post("/api/v1/users", json={"username": user_b})

    # Log translation for Alpha
    client.post("/api/v1/translate", json={
        "text": "Alpha secret transfer failed",
        "source_lang": "en",
        "target_lang": "ur",
        "session_id": "sess_alpha",
        "username": user_a
    })

    # Log translation for Beta
    client.post("/api/v1/translate", json={
        "text": "Beta secret transfer failed",
        "source_lang": "en",
        "target_lang": "ur",
        "session_id": "sess_beta",
        "username": user_b
    })

    # Verify Alpha history
    hist_a = client.get(f"/api/v1/history?username={user_a}").json()
    assert any("Alpha" in l["source_text"] for l in hist_a)
    assert not any("Beta" in l["source_text"] for l in hist_a)

    # Verify Beta history
    hist_b = client.get(f"/api/v1/history?username={user_b}").json()
    assert any("Beta" in l["source_text"] for l in hist_b)
    assert not any("Alpha" in l["source_text"] for l in hist_b)

def test_clear_user_history_preserves_other_users():
    """Verify clearing user A's logs deletes only user A's logs without affecting user B."""
    user_target = "user_clear_me"
    user_keep = "user_keep_me"

    client.post("/api/v1/users", json={"username": user_target})
    client.post("/api/v1/users", json={"username": user_keep})

    client.post("/api/v1/translate", json={
        "text": "Target log 1",
        "source_lang": "en",
        "target_lang": "ur",
        "username": user_target
    })
    client.post("/api/v1/translate", json={
        "text": "Keep log 1",
        "source_lang": "en",
        "target_lang": "ur",
        "username": user_keep
    })

    # Clear target user's history
    del_res = client.delete(f"/api/v1/users/{user_target}/history")
    assert del_res.status_code == 200

    # Target should be empty
    hist_target = client.get(f"/api/v1/history?username={user_target}").json()
    assert len(hist_target) == 0

    # Keep user should still have their log
    hist_keep = client.get(f"/api/v1/history?username={user_keep}").json()
    assert len(hist_keep) > 0

def test_protect_default_user_deletion():
    """Default user cannot be deleted."""
    res = client.delete("/api/v1/users/default")
    assert res.status_code == 400
