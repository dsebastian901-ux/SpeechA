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
