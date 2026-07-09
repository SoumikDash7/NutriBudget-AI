import sys
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_status(msg, success=True):
    symbol = "[PASS]" if success else "[FAIL]"
    print(f"{symbol} {msg}")

def get_otp_from_message(message):
    # Format is "OTP successfully sent to ... OTP is XXXXXX (in development mode)."
    try:
        parts = message.split("OTP is ")
        if len(parts) > 1:
            return parts[1].split(" ")[0]
    except Exception as e:
        print(f"Error parsing OTP: {e}")
    return None

async def register_user(client, email):
    # Send OTP
    res = await client.post("/auth/send-otp", json={
        "email_or_phone": email,
        "purpose": "register"
    })
    assert res.status_code == 200, f"send-otp failed: {res.text}"
    otp = get_otp_from_message(res.json()["message"])
    assert otp is not None, "Failed to get OTP from response in dev env"

    # Register (which internally verifies the OTP)
    res = await client.post("/auth/register", json={
        "email": email,
        "phone": None,
        "password": "Password123!",
        "otp_code": otp
    })
    assert res.status_code == 201, f"register failed: {res.text}"

    # Login
    res = await client.post("/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert res.status_code == 200, f"login failed: {res.text}"
    data = res.json()
    return data["tokens"]["access_token"], data["tokens"]["refresh_token"]

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create random emails for isolation
        email_a = f"test_{uuid.uuid4().hex[:6]}@example.com"
        email_b = f"test_{uuid.uuid4().hex[:6]}@example.com"
        email_c = f"test_{uuid.uuid4().hex[:6]}@example.com"

        print(f"Registering users:\n  User A: {email_a}\n  User B: {email_b}\n  User C: {email_c}")

        token_a, refresh_a = await register_user(client, email_a)
        token_b, refresh_b = await register_user(client, email_b)
        token_c, refresh_c = await register_user(client, email_c)

        print_status("Registered and logged in User A, User B, and User C")

        # ----------------------------------------------------
        # Task 1.1: Verify broken /auth/refresh endpoint
        # ----------------------------------------------------
        res = await client.post("/auth/refresh", json={"refresh_token": refresh_a})
        if res.status_code == 200:
            data = res.json()
            assert "access_token" in data and "refresh_token" in data
            print_status("Task 1.1: /auth/refresh returns 200 with new tokens")
        else:
            print_status(f"Task 1.1 failed: {res.text}", success=False)
            sys.exit(1)

        # Confirm invalid refresh token returns 401
        res = await client.post("/auth/refresh", json={"refresh_token": "invalid_refresh_token"})
        assert res.status_code == 401
        print_status("Task 1.1: Invalid refresh token returns 401 'Invalid refresh token.'")

        # ----------------------------------------------------
        # Task 1.2: Verify barcode lookup / Open Food Facts fallback
        # ----------------------------------------------------
        # Use known Nutella barcode on Open Food Facts
        res = await client.get("/calorie/barcode/3017620422003", headers={"Authorization": f"Bearer {token_a}"})
        if res.status_code == 200:
            data = res.json()
            assert "Nutella" in data["food_name"] or "nutella" in data["food_name"].lower()
            print_status(f"Task 1.2: Barcode lookup succeeded and returned product: {data['food_name']}")
        else:
            print_status(f"Task 1.2 failed: {res.text}", success=False)
            sys.exit(1)

        # ----------------------------------------------------
        # Task 2.2: Prevent refresh tokens from being usable as access tokens
        # ----------------------------------------------------
        res = await client.get("/profile/me", headers={"Authorization": f"Bearer {refresh_a}"})
        if res.status_code == 401:
            print_status("Task 2.2: Using refresh token as access token correctly returns 401")
        else:
            print_status(f"Task 2.2 failed: Using refresh token as access token returned {res.status_code}", success=False)
            sys.exit(1)

        # Access with normal access token should work (200 or 404 for missing profile, but NOT 401)
        res = await client.get("/profile/me", headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code != 401, f"Profile endpoint returned 401 for valid access token: {res.text}"
        print_status("Task 2.2: Using access token correctly does NOT return 401")

        # ----------------------------------------------------
        # Task 2.3: Add basic OTP rate limiting / attempt tracking
        # ----------------------------------------------------
        # Request a new OTP
        email_lim = f"limit_{uuid.uuid4().hex[:6]}@example.com"
        res = await client.post("/auth/send-otp", json={
            "email_or_phone": email_lim,
            "purpose": "register"
        })
        otp_correct = get_otp_from_message(res.json()["message"])

        # Try 5 wrong OTPs
        for i in range(5):
            res = await client.post("/auth/verify-otp", json={
                "email_or_phone": email_lim,
                "otp_code": "000000",
                "purpose": "register"
            })
            assert res.status_code == 400, f"Attempt {i+1} did not return 400: {res.text}"

        # 6th attempt with correct OTP should fail
        res = await client.post("/auth/verify-otp", json={
            "email_or_phone": email_lim,
            "otp_code": otp_correct,
            "purpose": "register"
        })
        if res.status_code == 400:
            print_status("Task 2.3: OTP lockout enforced after 5 failed attempts")
        else:
            print_status(f"Task 2.3 failed: 6th attempt with correct OTP succeeded: {res.text}", success=False)
            sys.exit(1)

        # ----------------------------------------------------
        # Task 3.4: Add basic upload validation to image scanning
        # ----------------------------------------------------
        # Upload a .txt file named as .jpg (simulate wrong content type)
        files = {"file": ("test.jpg", b"fake file content", "text/plain")}
        res = await client.post("/calorie/scan-image", files=files, headers={"Authorization": f"Bearer {token_a}"})
        if res.status_code == 415:
            print_status("Task 3.4: Uploading text file returned 415 Unsupported Media Type")
        else:
            print_status(f"Task 3.4 failed: Uploading text file returned {res.status_code}: {res.text}", success=False)
            sys.exit(1)

        # Upload a file larger than 10MB
        large_content = b"0" * (10 * 1024 * 1024 + 100)
        files = {"file": ("test.png", large_content, "image/png")}
        res = await client.post("/calorie/scan-image", files=files, headers={"Authorization": f"Bearer {token_a}"})
        if res.status_code == 413:
            print_status("Task 3.4: Uploading file > 10MB returned 413 Payload Too Large")
        else:
            print_status(f"Task 3.4 failed: Uploading large file returned {res.status_code}: {res.text}", success=False)
            sys.exit(1)

        # Upload a valid small file (verify filename heuristic fallback Task 3.3 triggers)
        files = {"file": ("apple.png", b"fake png bytes", "image/png")}
        res = await client.post("/calorie/scan-image", files=files, headers={"Authorization": f"Bearer {token_a}"})
        if res.status_code == 200:
            data = res.json()
            assert "Apple" in data["food_name"]
            print_status(f"Task 3.3 & 3.4: Valid small file upload succeeded, matched filename heuristic: {data['food_name']}")
        else:
            print_status(f"Task 3.3/3.4 failed: {res.text}", success=False)
            sys.exit(1)

        # ----------------------------------------------------
        # Task 1.4: Fix IDOR in shared budget transactions
        # ----------------------------------------------------
        # User A invites User B to collaborate
        res = await client.post("/budget/invite", json={
            "partner_email_or_phone": email_b,
            "name": "Shared A-B"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code == 201, f"collaboration invite failed: {res.text}"
        collab_id = res.json()["id"]

        # Accept collaboration as User B
        res = await client.post(f"/budget/invite/{collab_id}/respond", json={
            "status": "accepted"
        }, headers={"Authorization": f"Bearer {token_b}"})
        assert res.status_code == 200, f"respond to invite failed: {res.text}"

        # User A (authorized owner) adds transaction to collaboration
        res = await client.post("/budget/transaction", json={
            "amount": 25.50,
            "reason": "Groceries",
            "category": "Food",
            "date": "2026-07-08",
            "is_collaborative": True,
            "collaboration_id": str(collab_id)
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code == 201, f"authorized add failed: {res.text}"
        print_status("Task 1.4: Authorized owner A can add collaborative transaction")

        # User B (authorized partner) adds transaction to collaboration
        res = await client.post("/budget/transaction", json={
            "amount": 10.00,
            "reason": "Coffee",
            "category": "Food",
            "date": "2026-07-08",
            "is_collaborative": True,
            "collaboration_id": str(collab_id)
        }, headers={"Authorization": f"Bearer {token_b}"})
        assert res.status_code == 201, f"authorized partner B add failed: {res.text}"
        print_status("Task 1.4: Authorized partner B can add collaborative transaction")

        # User C (unauthorized) tries to add transaction to A-B collaboration
        res = await client.post("/budget/transaction", json={
            "amount": 100.00,
            "reason": "Malicious Injection",
            "category": "Food",
            "date": "2026-07-08",
            "is_collaborative": True,
            "collaboration_id": str(collab_id)
        }, headers={"Authorization": f"Bearer {token_c}"})
        if res.status_code == 400:
            print_status("Task 1.4: Unauthorized User C is blocked from adding transaction (IDOR prevented)")
        else:
            print_status(f"Task 1.4 failed: Unauthorized User C successfully added transaction: {res.text}", success=False)
            sys.exit(1)

        # Create a pending collaboration between A and C (C has not accepted yet)
        res = await client.post("/budget/invite", json={
            "partner_email_or_phone": email_c,
            "name": "Shared A-C Pending"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert res.status_code == 201, f"pending collaboration invite failed: {res.text}"
        pending_collab_id = res.json()["id"]

        # Attempt to add transaction to pending collaboration as User A
        res = await client.post("/budget/transaction", json={
            "amount": 5.00,
            "reason": "Wait for acceptance",
            "category": "Food",
            "date": "2026-07-08",
            "is_collaborative": True,
            "collaboration_id": str(pending_collab_id)
        }, headers={"Authorization": f"Bearer {token_a}"})
        if res.status_code == 400:
            print_status("Task 1.4: Adding transaction to pending collaboration is correctly blocked")
        else:
            print_status(f"Task 1.4 failed: User A added transaction to pending collaboration: {res.text}", success=False)
            sys.exit(1)

        # Clean up test accounts to keep DB tidy
        await client.delete("/auth/account", headers={"Authorization": f"Bearer {token_a}"})
        await client.delete("/auth/account", headers={"Authorization": f"Bearer {token_b}"})
        await client.delete("/auth/account", headers={"Authorization": f"Bearer {token_c}"})
        print_status("Cleaned up all temporary verification accounts successfully")

    print("\n*** ALL CHECKS PASSED SUCCESSFULLY! ***")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
