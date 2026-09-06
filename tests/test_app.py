def test_health():
    from app.main import app
    client = app.test_client()
    r = client.get("/health")
    assert r.status_code == 200
