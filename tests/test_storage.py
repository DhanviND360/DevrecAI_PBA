"""
Integration tests for DuckDB storage layer.
"""
import asyncio
import tempfile
from pathlib import Path
import pytest
from devrecai.storage.db import Database


@pytest.fixture
async def temp_db():
    """Provide a temporary in-memory/temp-file database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    db = Database(db_path=db_path)
    await db.init()
    yield db
    db.close()
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_session_crud(temp_db):
    """Test session create, read, list, delete."""
    db = temp_db
    profile = {"project_name": "TestProj", "team_size": "small"}
    results = {"categories": {"CI/CD": [{"name": "GitHub Actions", "score": 94}]}}

    # Create
    sid = await db.save_session(
        project_name="TestProj",
        profile=profile,
        results=results,
    )
    assert sid

    # Read
    session = await db.get_session(sid)
    assert session is not None
    assert session["project_name"] == "TestProj"
    assert session["profile_json"]["team_size"] == "small"

    # List
    sessions = await db.list_sessions()
    assert len(sessions) >= 1
    assert any(s["session_id"] == sid for s in sessions)

    # Delete
    await db.delete_session(sid)
    deleted = await db.get_session(sid)
    assert deleted is None


@pytest.mark.asyncio
async def test_feedback_crud(temp_db):
    """Test feedback save and count."""
    db = temp_db
    profile = {"project_name": "TestProj", "team_size": "small"}
    results = {}
    sid = await db.save_session("TestProj", profile, results)

    fid = await db.save_feedback(
        session_id=sid,
        tool_name="GitHub Actions",
        category="CI/CD",
        outcome_efficiency=4,
        outcome_adoption=5,
        outcome_stability=4,
        overall_score=4.3,
        notes="Works great",
    )
    assert fid

    count = await db.count_feedback()
    assert count >= 1


@pytest.mark.asyncio
async def test_training_log(temp_db):
    """Test training log insertion."""
    db = temp_db
    run_id = await db.save_training_log(
        sample_count=50,
        rmse=0.42,
        model_path="/tmp/model.json",
        feature_importances={"feat_0": 0.1, "feat_1": 0.9},
    )
    assert run_id
