from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re

from app.schemas import ConversationMessage
from app.services.privacy import mask_sensitive_data


class ConversationStore:
    def __init__(self, store_dir: Path) -> None:
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def append(self, session_id: str, role: str, content: str, domain: str | None = None, confidence: float | None = None) -> None:
        item = {
            "role": role,
            "content": mask_sensitive_data(content),
            "domain": domain,
            "confidence": confidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._path(session_id).open("a", encoding="utf-8") as file:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")

    def history(self, session_id: str, limit: int = 50) -> list[ConversationMessage]:
        path = self._path(session_id)
        if not path.exists():
            return []
        rows: list[ConversationMessage] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    rows.append(ConversationMessage(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    continue
        return rows[-limit:]

    def recent_context(self, session_id: str, limit: int = 6) -> str:
        messages = self.history(session_id, limit)
        return "\n".join(f"{item.role}: {item.content}" for item in messages)

    def _path(self, session_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)[:80]
        return self.store_dir / f"{safe}.jsonl"
