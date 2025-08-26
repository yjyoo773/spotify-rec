import pytest
from unittest.mock import patch, Mock
from app.spotify_client import get_playlist, get_playlist_tracks

@pytest.fixture
def fake_response():
    resp = Mock()
    resp.json.return_value = {"items": [], "next": None}
    resp.status_code = 200
    return resp

def test_get_playlist(fake_response):
    with patch("app.spotify_client.requests.request", return_value=fake_response) as mock_req:
        result = get_playlist("fake_token", "fake_playlist_id")
        assert result == {"items": [], "next": None}
        mock_req.assert_called_once()

def test_get_playlist_tracks_empty(fake_response):
    with patch("app.spotify_client.requests.request", return_value=fake_response):
        tracks = get_playlist_tracks("fake_token", "fake_playlist_id")
        assert tracks == []
