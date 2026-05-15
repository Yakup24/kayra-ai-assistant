from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
from uuid import uuid4

from app.schemas import UserProfile


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class AuthService:
    def __init__(
        self,
        database_path: Path,
        secret: str,
        admin_username: str,
        admin_password: str,
        support_username: str | None = None,
        support_password: str | None = None,
    ) -> None:
        self.database_path = database_path
        self.secret = secret.encode("utf-8")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._ensure_admin(admin_username, admin_password)
        if support_username and support_password:
            self._ensure_support(support_username, support_password)

    def create_user(
        self,
        *,
        username: str,
        password: str,
        email: str | None,
        display_name: str | None,
        role: str = "employee",
    ) -> UserProfile:
        normalized = username.strip().lower()
        safe_role = role if role in {"employee", "it", "hr", "support", "admin"} else "employee"
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (id, username, email, display_name, role, password_hash, active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        str(uuid4()),
                        normalized,
                        email.strip() if email else None,
                        display_name.strip() if display_name else normalized,
                        safe_role,
                        self._hash_password(password),
                        now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Bu kullanıcı adı zaten veritabanında kayıtlı.") from exc
        return self.get_user(normalized)

    def list_users(self) -> list[UserProfile]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, username, email, display_name, role, active FROM users ORDER BY role, username"
            ).fetchall()
        return [self._profile(dict(row)) for row in rows]

    def get_user(self, username: str) -> UserProfile:
        user = self._find_user(username, include_inactive=True)
        if not user:
            raise ValueError("Kullanıcı bulunamadı.")
        return self._profile(user)

    def set_user_active(self, username: str, active: bool) -> UserProfile:
        normalized = username.strip().lower()
        with self._connect() as conn:
            result = conn.execute("UPDATE users SET active = ? WHERE username = ?", (1 if active else 0, normalized))
            if result.rowcount == 0:
                raise ValueError("Kullanıcı bulunamadı.")
        return self.get_user(normalized)

    def reset_password(self, username: str, new_password: str) -> UserProfile:
        normalized = username.strip().lower()
        with self._connect() as conn:
            result = conn.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (self._hash_password(new_password), normalized),
            )
            if result.rowcount == 0:
                raise ValueError("Kullanıcı bulunamadı.")
        return self.get_user(normalized)

    def login(self, username: str, password: str) -> tuple[str, UserProfile]:
        user = self._find_user(username)
        if not user or not self._verify_password(password, user["password_hash"]):
            raise ValueError("Kullanıcı adı veya şifre hatalı.")
        profile = self._profile(user)
        return self.create_token(profile), profile

    def create_token(self, profile: UserProfile) -> str:
        payload = {
            "sub": profile.id,
            "username": profile.username,
            "role": profile.role,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=12)).timestamp()),
        }
        body = _b64encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        signature = _b64encode(hmac.new(self.secret, body.encode("ascii"), hashlib.sha256).digest())
        return f"{body}.{signature}"

    def verify_token(self, token: str) -> UserProfile:
        try:
            body, signature = token.split(".", 1)
            expected = _b64encode(hmac.new(self.secret, body.encode("ascii"), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Geçersiz imza.")
            payload = json.loads(_b64decode(body))
            if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
                raise ValueError("Oturum süresi doldu.")
        except Exception as exc:
            raise ValueError("Geçersiz oturum.") from exc

        user = self._find_user(str(payload["username"]))
        if not user:
            raise ValueError("Kullanıcı bulunamadı veya pasif.")
        return self._profile(user)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _ensure_admin(self, admin_username: str, admin_password: str) -> None:
        normalized_admin = admin_username.strip().lower()
        if self._find_user(normalized_admin, include_inactive=True):
            return
        self.create_user(
            username=normalized_admin,
            password=admin_password,
            email=None,
            display_name="Kayra Admin",
            role="admin",
        )

    def _ensure_support(self, support_username: str, support_password: str) -> None:
        normalized_support = support_username.strip().lower()
        if self._find_user(normalized_support, include_inactive=True):
            return
        self.create_user(
            username=normalized_support,
            password=support_password,
            email="kayra.destek@kayra.com",
            display_name="Kayra Destek Uzmanı",
            role="support",
        )

    def _find_user(self, username: str, include_inactive: bool = False) -> dict | None:
        normalized = username.strip().lower()
        sql = "SELECT id, username, email, display_name, role, password_hash, active FROM users WHERE username = ?"
        params: tuple = (normalized,)
        if not include_inactive:
            sql += " AND active = 1"
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
        return f"{salt}${digest.hex()}"

    def _verify_password(self, password: str, encoded: str) -> bool:
        salt, digest = encoded.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000).hex()
        return hmac.compare_digest(candidate, digest)

    def _profile(self, user: dict) -> UserProfile:
        return UserProfile(
            id=user["id"],
            username=user["username"],
            email=user.get("email"),
            display_name=user.get("display_name") or user["username"],
            role=user.get("role", "employee"),
            active=bool(user.get("active", 1)),
        )
