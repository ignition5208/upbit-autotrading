def test_upbit_keys(access: str, secret: str):
    # Stub: real implementation should call Upbit API with JWT.
    if not access or not secret:
        return False, "empty key"
    if len(access) < 10 or len(secret) < 10:
        return False, "too short"
    return True, "ok (stub)"
