"""Regression checks for local user access. No audio files required."""
import pytest
from app.services.auth_service import AuthService

def test_first_run_and_no_open_registration(tmp_path):
    service=AuthService(tmp_path/"accounts.db")
    assert service.needs_setup()
    service.initial_admin("admin01","Secure-password-001!")
    assert not service.needs_setup()
    with pytest.raises(PermissionError):
        service.initial_admin("admin02","Secure-password-002!")
    assert service.login("admin01","Secure-password-001!")["role"]=="administrador"

def test_permissions_and_revocation(tmp_path):
    service=AuthService(tmp_path/"accounts.db")
    service.initial_admin("admin01","Secure-password-001!")
    service.login("admin01","Secure-password-001!")
    service.create_user("supervisor1","Temp-supervisor-123!","supervisor")
    service.create_user("viewer1","Temp-consulta-123!","consulta")
    service.logout()
    assert service.login("supervisor1","Temp-supervisor-123!")["must_change"]
    assert not service.allowed("reports")
    service.change_password("Temp-supervisor-123!","New-supervisor-456!")
    assert service.allowed("reports")
    with pytest.raises(PermissionError):
        service.create_user("otheruser","Secure-password-123!","consulta")
    service.logout()
    service.login("admin01","Secure-password-001!")
    service.set_active("supervisor1",False)
    service.logout()
    with pytest.raises(PermissionError):
        service.login("supervisor1","New-supervisor-456!")

def test_admin_last_account_and_password_reset(tmp_path):
    service=AuthService(tmp_path/"accounts.db")
    service.initial_admin("admin01","Secure-password-001!")
    service.login("admin01","Secure-password-001!")
    with pytest.raises(ValueError):
        service.set_active("admin01",False)
    with pytest.raises(ValueError):
        service.set_role("admin01","consulta")
    service.create_user("viewer1","Temp-consulta-123!","consulta")
    service.reset_password("viewer1","Fresh-consulta-456!")
    service.logout()
    with pytest.raises(PermissionError):
        service.login("viewer1","Temp-consulta-123!")
    assert service.login("viewer1","Fresh-consulta-456!")["must_change"]

def test_failed_logins_lock(tmp_path):
    service=AuthService(tmp_path/"accounts.db")
    service.initial_admin("admin01","Secure-password-001!")
    for _ in range(5):
        with pytest.raises(PermissionError):
            service.login("admin01","incorrect")
    with pytest.raises(PermissionError):
        service.login("admin01","Secure-password-001!")

def test_passwords_not_in_database(tmp_path):
    db=tmp_path/"accounts.db"
    service=AuthService(db)
    service.initial_admin("admin01","Secure-password-001!")
    assert b"Secure-password-001!" not in db.read_bytes()

def test_supervisor_may_review_but_must_not_process_batches(tmp_path):
    service=AuthService(tmp_path/"accounts.db")
    service.initial_admin("admin01","Secure-password-001!")
    service.login("admin01","Secure-password-001!")
    service.create_user("supervisor1","Temp-supervisor-123!","supervisor")
    service.logout()
    service.login("supervisor1","Temp-supervisor-123!")
    service.change_password("Temp-supervisor-123!","New-supervisor-456!")
    assert service.allowed("manual_review")
    assert service.allowed("analytics")
    assert service.allowed("reports")
    assert not service.allowed("batch")
    with pytest.raises(PermissionError):
        service.require("batch")

def test_recovery_code_resets_locked_admin_and_is_single_use(tmp_path):
    service = AuthService(tmp_path/"users.sqlite3")
    code = service.initial_admin("DANIELA", "Original-admin-123!")
    assert isinstance(code, str) and len(code) >= 20
    for _ in range(5):
        with pytest.raises(PermissionError):
            service.login("DANIELA", "wrong")
    service.recover_password("DANIELA", code, "New-admin-password-123!")
    assert service.login("DANIELA", "New-admin-password-123!")["role"] == "administrador"
    service.logout()
    with pytest.raises(PermissionError):
        service.recover_password("DANIELA", code, "Different-password-123!")


def test_admin_can_reissue_recovery_code_for_existing_account(tmp_path):
    service = AuthService(tmp_path/"users.sqlite3")
    first = service.initial_admin("DANIELA", "Original-admin-123!")
    service.login("DANIELA", "Original-admin-123!")
    replacement = service.issue_recovery_code("DANIELA")
    assert replacement != first
    service.logout()
    with pytest.raises(PermissionError):
        service.recover_password("DANIELA", first, "Another-password-123!")
    service.recover_password("DANIELA", replacement, "Another-password-123!")


def test_recovery_requires_valid_code_and_respects_inactive_users(tmp_path):
    service = AuthService(tmp_path/"users.sqlite3")
    service.initial_admin("admin01", "Original-admin-123!")
    service.login("admin01", "Original-admin-123!")
    service.create_user("viewer01", "Temp-password-456!", "consulta")
    code = service.issue_recovery_code("viewer01")
    with pytest.raises(PermissionError):
        service.recover_password("viewer01", "invalid-code", "Different-password-123!")
    service.set_active("viewer01", False)
    service.logout()
    with pytest.raises(PermissionError):
        service.recover_password("viewer01", code, "Different-password-123!")

def test_recovery_lock_expiry_resets_bad_attempt_counter(tmp_path):
    import sqlite3
    from datetime import datetime, timedelta, timezone

    service = AuthService(tmp_path/"recovery_lock.sqlite3")
    code = service.initial_admin("DANIELA", "Initial-admin-password-123!")
    expired = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
    with sqlite3.connect(service.path) as conn:
        conn.execute("UPDATE recovery SET failed=5,locked_until=? WHERE username=?",
                     (expired,"DANIELA"))
    with pytest.raises(PermissionError):
        service.recover_password("DANIELA", "wrong-code", "New-password-123456!")
    with sqlite3.connect(service.path) as conn:
        failed,locked = conn.execute("SELECT failed,locked_until FROM recovery WHERE username=?",
                                     ("DANIELA",)).fetchone()
    assert failed == 1
    assert locked is None
    service.recover_password("DANIELA", code, "New-password-123456!")
    assert service.login("DANIELA", "New-password-123456!")["role"] == "administrador"


def test_existing_admin_must_issue_code_before_recovery(tmp_path):
    import sqlite3

    service = AuthService(tmp_path/"older_accounts.sqlite3")
    service.initial_admin("DANIELA", "Initial-admin-password-123!")
    with sqlite3.connect(service.path) as conn:
        conn.execute("DELETE FROM recovery WHERE username=?", ("DANIELA",))
    with pytest.raises(PermissionError):
        service.recover_password("DANIELA", "not-issued", "New-password-123456!")
    service.login("DANIELA", "Initial-admin-password-123!")
    code = service.issue_recovery_code("DANIELA")
    service.logout()
    service.recover_password("DANIELA", code, "New-password-123456!")
