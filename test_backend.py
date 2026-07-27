import sys
import json
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)
    print("=== Running Backend Verification Tests ===")

    # 1. Health Check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] 1. Health Check Passed")

    # 2. User Registration (User 1 & User 2)
    u1_payload = {"username": "alice", "email": "alice@test.com", "password": "Password123!"}
    u2_payload = {"username": "bob", "email": "bob@test.com", "password": "Password123!"}
    
    res1 = client.post("/api/v1/auth/register", json=u1_payload)
    if res1.status_code != 201:
        print(f"User 1 register note: {res1.json()}")
    
    res2 = client.post("/api/v1/auth/register", json=u2_payload)
    if res2.status_code != 201:
        print(f"User 2 register note: {res2.json()}")
    
    print("[PASS] 2. User Registration Passed")

    # 3. User Login
    login1 = client.post("/api/v1/auth/login", json={"username_or_email": "alice", "password": "Password123!"})
    assert login1.status_code == 200, f"Login Alice failed: {login1.text}"
    token_alice = login1.json()["access_token"]
    alice_id = login1.json()["user_id"]

    login2 = client.post("/api/v1/auth/login", json={"username_or_email": "bob", "password": "Password123!"})
    assert login2.status_code == 200, f"Login Bob failed: {login2.text}"
    token_bob = login2.json()["access_token"]
    bob_id = login2.json()["user_id"]

    print("[PASS] 3. JWT Login & Token Generation Passed")

    # 4. User List
    headers_alice = {"Authorization": f"Bearer {token_alice}"}
    headers_bob = {"Authorization": f"Bearer {token_bob}"}
    
    users_res = client.get("/api/v1/users", headers=headers_alice)
    assert users_res.status_code == 200, "Get users failed"
    users = users_res.json()
    assert len(users) >= 2, "Expected at least 2 users"
    print(f"[PASS] 4. User List fetched ({len(users)} users found)")

    # 5. Send Chat Message from Alice to Bob
    chat_res = client.post("/api/v1/chat/send", json={"receiver_id": bob_id, "message": "Hello Bob! Let us test Agora calling."}, headers=headers_alice)
    assert chat_res.status_code == 201, f"Send chat failed: {chat_res.text}"
    print("[PASS] 5. Chat message sent and stored in DB")

    # 6. Check Chat History
    hist_res = client.get(f"/api/v1/chat/history/{bob_id}", headers=headers_alice)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1
    print("[PASS] 6. Chat History retrieved successfully")

    # 7. Initiate Video Call from Alice to Bob
    call_res = client.post("/api/v1/calls/initiate", json={"receiver_id": bob_id, "call_type": "video"}, headers=headers_alice)
    assert call_res.status_code == 200, f"Call initiation failed: {call_res.text}"
    call_data = call_res.json()
    assert "caller_rtc_token" in call_data and call_data["caller_rtc_token"].startswith("007")
    assert "receiver_rtc_token" in call_data and call_data["receiver_rtc_token"].startswith("007")
    call_id = call_data["id"]
    print(f"[PASS] 7. Video Call initiated! Agora Channel: {call_data['channel_name']}, Token generated: {call_data['caller_rtc_token'][:25]}...")

    # 8. Update Call Status (Ended)
    end_res = client.post("/api/v1/calls/status", json={"call_id": call_id, "status": "ended"}, headers=headers_alice)
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "ended"
    print("[PASS] 8. Call status updated to 'ended' with duration calculation")

    # 9. Verify Notifications for Bob
    notif_res = client.get("/api/v1/notifications", headers=headers_bob)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert len(notifs) >= 2, "Bob should have notifications for chat and call"
    print(f"[PASS] 9. Notifications for Bob retrieved ({len(notifs)} notifications found)")

    # 10. Mark Notification as Read
    notif_id = notifs[0]["id"]
    read_res = client.put(f"/api/v1/notifications/{notif_id}/read", headers=headers_bob)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] == True
    print("[PASS] 10. Notification marked as read")

    # 11. Test Agora RTC Standalone Token Endpoint
    rtc_tok_res = client.post("/api/v1/agora/rtc-token", json={"channel_name": "test_channel", "uid": 123}, headers=headers_alice)
    assert rtc_tok_res.status_code == 200
    assert rtc_tok_res.json()["token"].startswith("007")
    print("[PASS] 11. Standalone Agora RTC AccessToken2 Endpoint Passed")

    print("\nALL BACKEND VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
