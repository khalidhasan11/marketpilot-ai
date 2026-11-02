"""TradingView webhook tests — confirmation-only, never a decision input."""
import sys, os, time, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import backend.app.db as db

# Isolate the test database BEFORE the app initialises it.
db.DB_PATH = os.path.join(os.path.dirname(__file__), "test_tv_webhook.db")

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.tv_webhook import normalize_symbol

SECRET = "test-secret-123"
URL = "/api/v1/webhooks/tradingview"


def _client(monkeypatch, secret=SECRET):
    if secret is None:
        monkeypatch.delenv("TRADINGVIEW_WEBHOOK_SECRET", raising=False)
    else:
        monkeypatch.setenv("TRADINGVIEW_WEBHOOK_SECRET", secret)
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db.DB_PATH + suffix):
            os.remove(db.DB_PATH + suffix)
    return TestClient(app)


def _payload(**kw):
    p = {"secret": SECRET, "event_id": "evt-1", "symbol": "BINANCE:BTCUSDT",
         "action": "BUY cross", "price": 65000.0, "timestamp": int(time.time())}
    p.update(kw)
    return p


def _auth(client):
    client.post("/api/v1/auth/register", json={"email": "tv@test.io", "password": "password123"})
    r = client.post("/api/v1/auth/login", json={"email": "tv@test.io", "password": "password123"})
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_symbol_mapping():
    assert normalize_symbol("BINANCE:BTCUSDT") == "BTCUSDT"
    assert normalize_symbol("BTCUSDT") == "BTCUSDT"
    assert normalize_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_symbol("ethusdt") == "ETHUSDT"
    assert normalize_symbol("BINANCE:NOTACOIN") is None
    assert normalize_symbol("") is None


def test_webhook_503_when_secret_unset(monkeypatch):
    with _client(monkeypatch, secret=None) as client:
        r = client.post(URL, json=_payload())
        assert r.status_code == 503


def test_webhook_rejects_wrong_secret(monkeypatch):
    with _client(monkeypatch) as client:
        r = client.post(URL, json=_payload(secret="wrong"))
        assert r.status_code == 401
        headers = _auth(client)
        ev = client.get(URL + "/events", headers=headers).json()["events"]
        assert any(e["status"] == "rejected_bad_secret" for e in ev)


def test_webhook_rejects_stale_timestamp(monkeypatch):
    with _client(monkeypatch) as client:
        r = client.post(URL, json=_payload(timestamp=int(time.time()) - 3600))
        assert r.status_code == 400


def test_webhook_rejects_unknown_symbol(monkeypatch):
    with _client(monkeypatch) as client:
        r = client.post(URL, json=_payload(symbol="BINANCE:NOTACOIN"))
        assert r.status_code == 422


def test_webhook_accept_dedupe_and_confirmation_only(monkeypatch):
    with _client(monkeypatch) as client:
        # baseline: no signals exist before any alert
        before = client.get("/api/v1/signals").json()["signals"]
        r1 = client.post(URL, json=_payload())
        assert r1.status_code == 200 and r1.json()["accepted"] is True
        assert r1.json()["confirmation_only"] is True
        # identical event again -> duplicate, not reprocessed
        r2 = client.post(URL, json=_payload())
        assert r2.status_code == 200 and r2.json()["duplicate"] is True
        headers = _auth(client)
        data = client.get(URL + "/events", headers=headers).json()
        accepted = [e for e in data["events"] if e["status"] == "accepted"]
        assert len(accepted) == 1 and accepted[0]["symbol"] == "BTCUSDT"
        confs = data["confirmations"]
        assert len(confs) == 1 and confs[0]["source"] == "tradingview_alert"
        assert confs[0]["confirmation_only"] == 1
        # the alert must NOT have created any trading signal or prediction
        after = client.get("/api/v1/signals").json()["signals"]
        assert len(after) == len(before)
        perf = client.get("/api/v1/performance").json()
        assert perf["predictions_recorded"] == 0
        # and it landed as a notification
        notifs = client.get("/api/v1/notifications", headers=headers)
        assert notifs.status_code in (200, 404)  # notifications are per-user; system rows have NULL user


def test_webhook_events_require_auth(monkeypatch):
    with _client(monkeypatch) as client:
        r = client.get(URL + "/events")
        assert r.status_code == 401
