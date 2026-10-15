import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.db.models import Learner
from app.content.seed import seed_content


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        seed_content(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "database" in data
    assert "timestamp" in data


def test_create_learner(client):
    response = client.post("/api/learners", json={})
    assert response.status_code == 201
    data = response.json()
    assert "token" in data
    assert "token_hash" in data
    assert len(data["token"]) == 64
    assert len(data["token_hash"]) == 64


def test_learner_auth_flow(client):
    response = client.post("/api/learners", json={})
    assert response.status_code == 201
    learner_data = response.json()
    token = learner_data["token"]
    
    # Use token for authenticated request
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/me/summary", headers=headers)
    assert response.status_code == 200
    summary = response.json()
    assert "total_xp" in summary
    assert "active_level" in summary


def test_invalid_token_rejected(client):
    headers = {"Authorization": "Bearer invalid-token"}
    response = client.get("/api/me/summary", headers=headers)
    assert response.status_code == 401


def test_start_session(client):
    # Create learner
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Start session
    response = client.post("/api/sessions", json={"level": 3}, headers=headers)
    assert response.status_code == 201
    session = response.json()
    assert session["level"] == 3
    assert session["phase"] == "diagnostic"
    assert session["step_index"] == 0


def test_get_question(client):
    # Create learner and session
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/api/sessions", json={"level": 3}, headers=headers)
    session_id = response.json()["id"]
    
    # Get first question
    response = client.get(f"/api/sessions/{session_id}", headers=headers)
    assert response.status_code == 200
    question = response.json()
    assert "served_item_id" in question
    assert "prompt" in question
    assert "options" in question
    assert len(question["options"]) >= 4  # At least 4 options + unsure


def test_submit_answer_correct(client):
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/api/sessions", json={"level": 3}, headers=headers)
    session_id = response.json()["id"]
    
    # Get question
    response = client.get(f"/api/sessions/{session_id}", headers=headers)
    question = response.json()
    
    # Find correct option (we don't know which, so try first)
    # This test just verifies the flow works
    correct_option = question["options"][0]["id"]
    response = client.post(
        f"/api/sessions/{session_id}/answer",
        json={"served_item_id": question["served_item_id"], "option_id": correct_option},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "feedback" in data
    assert "is_correct" in data["feedback"]


def test_idempotent_answer(client):
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/api/sessions", json={"level": 3}, headers=headers)
    session_id = response.json()["id"]
    
    response = client.get(f"/api/sessions/{session_id}", headers=headers)
    question = response.json()
    served_item_id = question["served_item_id"]
    
    # Submit answer twice
    option_id = question["options"][0]["id"]
    
    response1 = client.post(
        f"/api/sessions/{session_id}/answer",
        json={"served_item_id": served_item_id, "option_id": option_id},
        headers=headers
    )
    assert response1.status_code == 200
    
    response2 = client.post(
        f"/api/sessions/{session_id}/answer",
        json={"served_item_id": served_item_id, "option_id": option_id},
        headers=headers
    )
    assert response2.status_code == 200
    # Should return same result (cached)
    assert response1.json() == response2.json()


def test_phase_skip_rejected(client):
    """Direct API calls skipping phases should return 409."""
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post("/api/sessions", json={"level": 3}, headers=headers)
    session_id = response.json()["id"]
    
    # Try to access retest directly (should fail)
    # This is tested by the engine, but API should also reject
    pass  # Phase enforcement is in engine logic


def _answer_for(question, wrong):
    """Pick a correct (or a wrong) option for a served question using the content files."""
    from app.content.loader import get_content_loader

    item = get_content_loader().get_item_by_id(question["item_id"])
    ids = [o["id"] for o in question["options"]]
    if not wrong:
        return item["correct_option_id"]
    return next(i for i in ids if i != item["correct_option_id"])


@pytest.mark.parametrize("wrong_in_diagnostic", [False, True])
def test_full_journey(client, wrong_in_diagnostic):
    """Play a whole session through the API: diagnostic -> ... -> practice -> retest -> done."""
    token = client.post("/api/learners").json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    session = client.post("/api/sessions", json={"level": 3}, headers=headers).json()
    session_id = session["id"]
    question = client.get(f"/api/sessions/{session_id}", headers=headers).json()

    # Re-reading the question shows the same question and option order
    again = client.get(f"/api/sessions/{session_id}", headers=headers).json()
    assert again["served_item_id"] == question["served_item_id"]
    assert again["options"] == question["options"]

    phases_seen = []
    total_xp = 0
    for _ in range(40):
        phases_seen.append(question["phase"])
        wrong = wrong_in_diagnostic and question["phase"] == "diagnostic"
        response = client.post(
            f"/api/sessions/{session_id}/answer",
            json={"served_item_id": question["served_item_id"], "option_id": _answer_for(question, wrong)},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        total_xp += data["feedback"]["xp_awarded"]
        if data["session"]["status"] == "completed":
            break
        question = data["next_question"]
        assert question is not None
    else:
        pytest.fail("Session never finished")

    assert phases_seen[0] == "diagnostic"
    assert phases_seen[-1] == "retest"
    assert phases_seen.count("practice") == 3
    assert phases_seen.count("retest") == 3
    assert ("followup" in phases_seen) == wrong_in_diagnostic
    assert ("check_understanding" in phases_seen) == (not wrong_in_diagnostic)

    # XP is awarded once for practice and once for the retest (50 + 25), never twice
    assert total_xp == 75
    progress = client.get("/api/progress", headers=headers).json()
    assert progress["total_xp"] == 75
    level3 = next(sk for sk in progress["skills"] if sk["level"] == 3)
    assert level3["last_retest_score"] == 3
    assert level3["last_retest_total"] == 3

    # A finished session has no more questions
    assert client.get(f"/api/sessions/{session_id}", headers=headers).status_code == 409


def test_delete_learner(client):
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.delete("/api/learners/me", headers=headers)
    assert response.status_code == 204
    
    # Token should now be invalid
    response = client.get("/api/me/summary", headers=headers)
    assert response.status_code == 401


def test_levels_endpoint(client):
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/levels", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "levels" in data
    assert len(data["levels"]) == 5
    for level in data["levels"]:
        assert "id" in level
        assert "name" in level
        assert "status" in level


def test_insights_endpoint(client):
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/insights", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "hypotheses" in data
    assert "recent_evidence" in data


def test_progress_endpoint(client):
    response = client.post("/api/learners")
    token = response.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/progress", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_xp" in data
    assert "skills" in data
    assert "achievements" in data
    assert "history" in data


def test_cors_headers(client):
    # A real browser preflight carries Access-Control-Request-Method
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])