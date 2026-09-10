from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


def test_github_install_redirect():
    client = TestClient(app, follow_redirects=False)
    settings.GITHUB_APP_SLUG = "mergemindd"
    response = client.get("/api/github/install")
    assert response.status_code == 307
    assert response.headers["location"] == "https://github.com/apps/mergemindd/installations/new"


def test_github_install_missing_slug():
    client = TestClient(app, follow_redirects=False)
    settings.GITHUB_APP_SLUG = ""
    response = client.get("/api/github/install")
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "GITHUB_APP_SLUG" in data["detail"]
    # Verify no credentials leaked
    assert "secret" not in str(data).lower()
    assert "private" not in str(data).lower()
    # Reset back to original
    settings.GITHUB_APP_SLUG = "mergemindd"
