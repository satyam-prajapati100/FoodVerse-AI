import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "5. Project Development Phase" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app

client = TestClient(app)
TEST_IMAGE = BACKEND_DIR / "food_test.jpg"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()


def test_unknown_endpoint_returns_404():
    response = client.get("/this-endpoint-does-not-exist")
    assert response.status_code == 404


def test_preprocess_valid_image():
    assert TEST_IMAGE.is_file(), f"Test image not found: {TEST_IMAGE}"

    with TEST_IMAGE.open("rb") as image:
        response = client.post(
            "/image/preprocess",
            files={"file": ("food_test.jpg", image, "image/jpeg")},
        )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["success"] is True
    assert data["filename"] == "food_test.jpg"
    assert data["processed_image"]["width"] > 0
    assert data["processed_image"]["height"] > 0
    assert "features" in data


def test_preprocess_rejects_non_image_content_type():
    response = client.post(
        "/image/preprocess",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Please upload an image file."


def test_preprocess_rejects_empty_image():
    response = client.post(
        "/image/preprocess",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded image is empty."


if __name__ == "__main__":
    print("Run these tests with: python -m pytest")
