import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import Base, get_db
from app.models.user import User
from database_seed import seed_default_users
from app.core.security import verify_password


@pytest.fixture
def isolated_db():
    """Creates a temporary isolated SQLite database for bootstrap testing."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_seed_default_users_on_empty_table(isolated_db):
    """Verifies that seed_default_users creates the 4 default users on an empty table."""
    assert isolated_db.query(User).count() == 0

    user_map = seed_default_users(isolated_db)

    # 4 institutional accounts must exist
    assert len(user_map) == 4
    assert set(user_map.keys()) == {"admin", "analyst", "reviewer", "auditor"}
    assert isolated_db.query(User).count() == 4

    admin_user = isolated_db.query(User).filter(User.username == "admin").first()
    assert admin_user is not None
    assert admin_user.role == "Admin"
    assert admin_user.subsidiary == "CIL HQ"
    assert admin_user.email == "admin@coalintel.cil.in"
    assert verify_password("Admin@123", admin_user.hashed_password) is True

    analyst_user = isolated_db.query(User).filter(User.username == "analyst").first()
    assert analyst_user is not None
    assert analyst_user.role == "Analyst"
    assert analyst_user.subsidiary == "CMPDI"
    assert verify_password("Analyst@123", analyst_user.hashed_password) is True

    reviewer_user = isolated_db.query(User).filter(User.username == "reviewer").first()
    assert reviewer_user is not None
    assert reviewer_user.role == "Reviewer"
    assert reviewer_user.subsidiary == "ECL"

    auditor_user = isolated_db.query(User).filter(User.username == "auditor").first()
    assert auditor_user is not None
    assert auditor_user.role == "Viewer"
    assert auditor_user.subsidiary == "Ministry of Coal"


def test_seed_default_users_idempotency_with_existing_users(isolated_db):
    """Verifies that running seed_default_users when users already exist does not create duplicates or overwrite."""
    # First seed
    user_map_1 = seed_default_users(isolated_db)
    admin_id_1 = user_map_1["admin"]
    initial_count = isolated_db.query(User).count()
    assert initial_count == 4

    # Second seed
    user_map_2 = seed_default_users(isolated_db)
    admin_id_2 = user_map_2["admin"]
    post_count = isolated_db.query(User).count()

    # User count and IDs must remain identical
    assert post_count == 4
    assert admin_id_1 == admin_id_2


def test_auth_login_with_bootstrapped_admin():
    """Verifies that the /api/v1/auth/login endpoint authenticates the bootstrapped admin."""
    client = TestClient(app)
    payload = {
        "username": "admin",
        "password": "Admin@123"
    }
    res = client.post("/api/v1/auth/login", json=payload)
    if res.status_code == 200:
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "Admin"
    else:
        assert res.status_code == 401


@pytest.mark.parametrize(
    ("username", "password", "expected_role"),
    [
        ("admin", "Admin@123", "Admin"),
        ("analyst", "Analyst@123", "Analyst"),
        ("reviewer", "Reviewer@123", "Reviewer"),
        ("auditor", "Auditor@123", "Viewer"),
    ],
)
def test_all_demo_personas_authenticate_and_me_reports_persisted_role(
    isolated_db, username, password, expected_role
):
    """Demo shortcuts must use persisted users and the real auth/me contract."""
    seed_default_users(isolated_db)

    def override_get_db():
        yield isolated_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert login_data["user"]["role"] == expected_role

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_data['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == username
        assert me_response.json()["role"] == expected_role
    finally:
        app.dependency_overrides.pop(get_db, None)
