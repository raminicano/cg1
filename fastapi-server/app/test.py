from fastapi.testclient import TestClient
from myapp import app  # FastAPI 앱 모듈을 가져옵니다.

client = TestClient(app)

def test_api_integration():
    # 첫 번째 API 호출
    response = client.get("/fetch_realtime?location=Seoul")
    assert response.status_code == 200
    data_to_add = response.json()

    # 두 번째 API 호출
    response = client.post("/mongo/add_data", json={"collection_name": "your_collection", "item": data_to_add})
    assert response.status_code == 201
    assert "message" in response.json()

# 테스트 실행
test_api_integration()