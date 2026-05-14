from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64
import hashlib
import hmac
import json
import secrets
from typing import Any
from uuid import uuid4

from app.schemas import UserProfile
from app.services.privacy import mask_sensitive_data


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class AuthService:
    def __init__(self, store_path: Path, secret: str, admin_username: str, admin_password: str) -> None:
        self.store_path = store_path
        self.secret = secret.encode("utf-8")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_store(admin_username, admin_password)

    def register(self, username: str, password: str, email: str | None, display_name: str | None) -> UserProfile:
        store = self._load()
        normalized = username.strip().lower()
        if normalized in store["users"]:
            raise ValueError("Bu kullanıcı adı zaten kayıtlı.")

        user = {
            "id": str(uuid4()),
            "username": normalized,
            "email": mask_sensitive_data(email.strip()) if email else None,
            "display_name": display_name.strip() if display_name else normalized,
            "role": "employee",
            "password": self._hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        store["users"][normalized] = user
        self._save(store)
        return self._profile(user)

    def login(self, username: str, password: str) -> tuple[str, UserProfile]:
        user = self._find_user(username)
        if not user or not self._verify_password(password, user["password"]):
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
            raise ValueError("Kullanıcı bulunamadı.")
        return self._profile(user)

    def _ensure_store(self, admin_username: str, admin_password: str) -> None:
        store = self._load()
        normalized_admin = admin_username.strip().lower()
        if normalized_admin not in store["users"]:
            store["users"][normalized_admin] = {
                "id": str(uuid4()),
                "username": normalized_admin,
                "email": None,
                "display_name": "Kayra Admin",
                "role": "admin",
                "password": self._hash_password(admin_password),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save(store)

    def _find_user(self, username: str) -> dict[str, Any] | None:
        return self._load()["users"].get(username.strip().lower())

    def _load(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"users": {}}
        with self.store_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self, store: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=False, indent=2)

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000)
        return f"{salt}${digest.hex()}"

    def _verify_password(self, password: str, encoded: str) -> bool:
        salt, digest = encoded.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 120_000).hex()
        return hmac.compare_digest(candidate, digest)

    def _profile(self, user: dict[str, Any]) -> UserProfile:
        return UserProfile(
            id=user["id"],
            username=user["username"],
            email=user.get("email"),
            display_name=user.get("display_name") or user["username"],
            role=user.get("role", "employee"),
        )
