"""Local authentication and role authorization. No default credentials."""
from __future__ import annotations
import hashlib
import hmac
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROLES = ("administrador", "calidad", "supervisor", "consulta")
PERMISSIONS = {
 "administrador": frozenset(("home","projects","audio","transcriptions","analytics","dashboard","batch","reports","history","settings","users","manual_review")),
 "calidad": frozenset(("home","projects","audio","transcriptions","analytics","dashboard","batch","reports","history","manual_review")),
 "supervisor": frozenset(("home","projects","audio","transcriptions","analytics","dashboard","reports","history","manual_review")),
 "consulta": frozenset(("home","dashboard")),
}
ITERATIONS = 600000
MAX_FAILURES = 5
LOCK_MINUTES = 15

def _db_path():
    home = os.environ.get("LOCALAPPDATA")
    if not home:
        home = str(Path.home() / "AppData" / "Local") if sys.platform == "win32" else str(Path.home() / ".local" / "share")
    folder = Path(home) / "MRS" / "SpeechAnalytics"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "usuarios.sqlite3"

def _now():
    return datetime.now(timezone.utc).isoformat()

def _hash(password, salt=None):
    salt = os.urandom(16) if salt is None else salt
    return salt.hex(), hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()

def _validate(username, password):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,48}", username):
        raise ValueError("Usuario: 3 a 48 caracteres (letras, números, punto, guion).")
    if len(password) < 12 or len(password) > 256:
        raise ValueError("La contraseña debe tener entre 12 y 256 caracteres.")

class AuthService:
    def __init__(self, db_path=None):
        self.path = str(db_path or _db_path())
        self.current_user = None
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                salt TEXT NOT NULL, hash TEXT NOT NULL,
                role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                failed INTEGER NOT NULL DEFAULT 0, locked_until TEXT,
                must_change INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL, actor TEXT, event TEXT NOT NULL, target TEXT)""")

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _audit(self, conn, actor, event, target=None):
        conn.execute("INSERT INTO audit(created_at,actor,event,target) VALUES(?,?,?,?)", (_now(), actor, event, target))

    def needs_setup(self):
        with self._connect() as conn:
            return conn.execute("SELECT NOT EXISTS(SELECT 1 FROM users)").fetchone()[0] == 1

    def initial_admin(self, username, password):
        _validate(username, password)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                raise PermissionError("Ya existe una cuenta; el registro inicial está cerrado.")
            salt, digest = _hash(password)
            conn.execute("INSERT INTO users(username,salt,hash,role,created_at) VALUES(?,?,?,?,?)",
                         (username, salt, digest, "administrador", _now()))
            self._audit(conn, username, "initial_admin", username)

    def login(self, username, password):
        self.current_user = None
        with self._connect() as conn:
            row = conn.execute("SELECT username,salt,hash,role,active,failed,locked_until,must_change FROM users WHERE username=?", (username.strip(),)).fetchone()
            if row is None:
                _hash(password)  # comparable cost for nonexistent users
                self._audit(conn, None, "login_failed", None)
                raise PermissionError("Credenciales inválidas o cuenta bloqueada.")
            name, salt, digest, role, active, failed, locked, must_change = row
            if not active or (locked and datetime.fromisoformat(locked) > datetime.now(timezone.utc)):
                self._audit(conn, name, "login_rejected", name)
                raise PermissionError("Credenciales inválidas o cuenta bloqueada.")
            _, candidate = _hash(password, bytes.fromhex(salt))
            if not hmac.compare_digest(candidate, digest):
                failed += 1
                until = (datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)).isoformat() if failed >= MAX_FAILURES else None
                conn.execute("UPDATE users SET failed=?,locked_until=? WHERE username=?", (failed, until, name))
                self._audit(conn, name, "login_failed", name)
                raise PermissionError("Credenciales inválidas o cuenta bloqueada.")
            conn.execute("UPDATE users SET failed=0,locked_until=NULL WHERE username=?", (name,))
            self._audit(conn, name, "login", name)
            self.current_user = {"username":name,"role":role,"must_change":bool(must_change)}
            return dict(self.current_user)

    def logout(self):
        if self.current_user:
            with self._connect() as conn:
                self._audit(conn, self.current_user["username"], "logout")
        self.current_user = None

    def allowed(self, permission):
        if not self.current_user:
            return False
        with self._connect() as conn:
            row=conn.execute("SELECT role,active,must_change FROM users WHERE username=?",
                             (self.current_user["username"],)).fetchone()
        if not row or not row[1] or row[2]:
            return False
        self.current_user["role"]=row[0]
        return permission in PERMISSIONS.get(row[0],())

    def require(self, permission):
        if not self.allowed(permission):
            raise PermissionError("No tiene permiso para ejecutar esta operación.")

    def _admin(self):
        self.require("users")

    def users(self):
        self._admin()
        with self._connect() as conn:
            return conn.execute("SELECT username,role,active,must_change FROM users ORDER BY username").fetchall()

    def create_user(self, username, password, role):
        self._admin()
        _validate(username, password)
        if role not in ROLES:
            raise ValueError("Rol desconocido.")
        salt, digest = _hash(password)
        with self._connect() as conn:
            conn.execute("INSERT INTO users(username,salt,hash,role,must_change,created_at) VALUES(?,?,?,?,1,?)",
                         (username,salt,digest,role,_now()))
            self._audit(conn,self.current_user["username"],"user_created",username)

    def change_password(self, old_password, new_password):
        if not self.current_user:
            raise PermissionError("Inicie sesión.")
        name = self.current_user["username"]
        _validate(name,new_password)
        with self._connect() as conn:
            row = conn.execute("SELECT salt,hash FROM users WHERE username=?",(name,)).fetchone()
            if not row or not hmac.compare_digest(_hash(old_password,bytes.fromhex(row[0]))[1],row[1]):
                raise PermissionError("Contraseña actual incorrecta.")
            salt,digest = _hash(new_password)
            conn.execute("UPDATE users SET salt=?,hash=?,must_change=0 WHERE username=?",(salt,digest,name))
            self._audit(conn,name,"password_changed",name)
        self.current_user["must_change"] = False

    def reset_password(self, username, new_password):
        self._admin()
        _validate(username,new_password)
        salt,digest = _hash(new_password)
        with self._connect() as conn:
            cursor=conn.execute("UPDATE users SET salt=?,hash=?,must_change=1,failed=0,locked_until=NULL WHERE username=?",(salt,digest,username))
            if not cursor.rowcount:
                raise ValueError("Usuario no encontrado.")
            self._audit(conn,self.current_user["username"],"password_reset",username)

    def set_role(self, username, role):
        self._admin()
        if role not in ROLES:
            raise ValueError("Rol no válido.")
        with self._connect() as conn:
            current=conn.execute("SELECT role,active FROM users WHERE username=?",(username,)).fetchone()
            if not current:
                raise ValueError("Usuario no encontrado.")
            if current[0] == "administrador" and current[1] and role != "administrador":
                count=conn.execute("SELECT COUNT(*) FROM users WHERE role='administrador' AND active=1").fetchone()[0]
                if count <= 1:
                    raise ValueError("Debe conservarse un administrador activo.")
            conn.execute("UPDATE users SET role=? WHERE username=?",(role,username))
            self._audit(conn,self.current_user["username"],"role_changed",username)

    def set_active(self, username, active):
        self._admin()
        if username.casefold() == self.current_user["username"].casefold() and not active:
            raise ValueError("No puede desactivar su propia cuenta.")
        with self._connect() as conn:
            row=conn.execute("SELECT role,active FROM users WHERE username=?",(username,)).fetchone()
            if not row:
                raise ValueError("Usuario no encontrado.")
            if row[0] == "administrador" and row[1] and not active:
                count=conn.execute("SELECT COUNT(*) FROM users WHERE role='administrador' AND active=1").fetchone()[0]
                if count <= 1:
                    raise ValueError("Debe conservarse un administrador activo.")
            conn.execute("UPDATE users SET active=? WHERE username=?",(int(bool(active)),username))
            self._audit(conn,self.current_user["username"],"user_enabled" if active else "user_disabled",username)

    def recent_audit(self, limit=100):
        self._admin()
        with self._connect() as conn:
            return conn.execute("SELECT created_at,actor,event,target FROM audit ORDER BY id DESC LIMIT ?",(min(int(limit),500),)).fetchall()
