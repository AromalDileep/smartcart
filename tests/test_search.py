from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_search_text():
    # Mock the search service to avoid loading the model
    with patch("app.routers.search.search_by_text") as mock_search:
        mock_search.return_value = {
            "results": [{"id": 1, "score": 0.9}],
            "time_taken": 0.1
        }
        
        # Test a basic text search
        # We expect a 200 OK even if no results are found
        # Endpoint is /search/text with query param 'query'
        response = client.get("/search/text?query=test_query")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert "time_taken" in data
