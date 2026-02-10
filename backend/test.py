import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_health_check():
    """Simple check to see if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        assert response.status_code == 200
    except requests.exceptions.ConnectionError:
        pytest.fail("Server is not running. Start main.py first.")

def test_recommendation_search():
    """Test if searching for 'dreams' finds Inception."""
    payload = {"message": "I want a movie about dreams"}
    response = requests.post(f"{BASE_URL}/agent", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Allow RECOMMEND or SEARCH (both are valid for this query)
    assert data["tool_used"] in ["RECOMMEND", "SEARCH"]
    
    # Check if the correct movie is found (Alignment Check)
    assert "Inception" in data["response"]

def test_rag_question():
    """
    STRICT OBJECTIVE CHECK:
    Questions about specific details MUST use RAG.
    """
    payload = {"message": "Who cooks in Ratatouille?"}
    response = requests.post(f"{BASE_URL}/agent", json=payload)

    assert response.status_code == 200
    data = response.json()

    # STRICT ASSERTION: If this fails, the Router prompt needs fixing.
    assert data["tool_used"] == "RAG"
    
    # Check if the answer is factually correct based on the DB
    assert "rat" in data["response"].lower() or "remy" in data["response"].lower()

def test_unknown_query():
    """Test how the system handles nonsense."""
    payload = {"message": "xgdfgdfgsdgsd"}
    response = requests.post(f"{BASE_URL}/agent", json=payload)

    assert response.status_code == 200
    
    # FIX: Added the missing line that caused the NameError
    data = response.json() 

    # Should be a polite refusal, not a crash or a random movie
    assert "sorry" in data["response"].lower() or "nothing" in data["response"].lower()