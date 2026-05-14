from datetime import datetime, timezone
from pathlib import Path
import json

from app.services.privacy import mask_sensitive_data


class AnalyticsLogger:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.log_dir / "chat_events.jsonl"
        self.feedback_file = self.log_dir / "feedback.jsonl"

    def log_chat(self, payload: dict) -> None:
        self._append(self.events_file, payload)

    def log_feedback(self, payload: dict) -> None:
        self._append(self.feedback_file, payload)

    def recent_events(self, limit: int = 20) -> list[dict]:
        return self._read_jsonl(self.events_file, limit)

    def recent_feedback(self, limit: int = 20) -> list[dict]:
        return self._read_jsonl(self.feedback_file, limit)

    def summary(self) -> dict:
        events = self._read_jsonl(self.events_file, limit=1000)
        feedback = self._read_jsonl(self.feedback_file, limit=1000)
        total = len(events)
        avg_confidence = 0.0
        if total:
            avg_confidence = sum(float(event.get("confidence", 0) or 0) for event in events) / total
        handoffs = sum(1 for event in events if event.get("handoff_recommended"))
        low_confidence = sum(1 for event in events if float(event.get("confidence", 0) or 0) < 0.45)
        avg_rating = 0.0
        if feedback:
            avg_rating = sum(int(item.get("rating", 0) or 0) for item in feedback) / len(feedback)
        return {
            "total_chats": total,
            "avg_confidence": round(avg_confidence, 2),
            "handoffs": handoffs,
            "low_confidence": low_confidence,
            "feedback_count": len(feedback),
            "avg_rating": round(avg_rating, 1),
        }

    def _append(self, path: Path, payload: dict) -> None:
        sanitized = {
            key: mask_sensitive_data(value) if isinstance(value, str) else value
            for key, value in payload.items()
        }
        sanitized["created_at"] = datetime.now(timezone.utc).isoformat()
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(sanitized, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path, limit: int) -> list[dict]:
        if not path.exists():
            return []
        rows: list[dict] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows[-limit:]
