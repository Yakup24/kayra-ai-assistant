from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from app.schemas import IntegrationConfig, KnowledgeDocumentInfo, TicketDraftResponse, TicketRecord


DEFAULT_INTEGRATIONS = [
    {
        "id": "graph",
        "name": "Microsoft Graph / Exchange",
        "category": "E-posta",
        "status": "Planlandı",
        "enabled": 0,
        "endpoint": "https://graph.microsoft.com",
        "description": "Gelen destek e-postalarını sınıflandırma ve cevap taslağı üretme.",
    },
    {
        "id": "jira",
        "name": "Jira Service Management",
        "category": "Ticket",
        "status": "Hazır adaptör",
        "enabled": 0,
        "endpoint": "",
        "description": "Chat akışından issue/talep kaydı açma ve SLA takibi.",
    },
    {
        "id": "servicenow",
        "name": "ServiceNow",
        "category": "Ticket",
        "status": "Planlandı",
        "enabled": 0,
        "endpoint": "",
        "description": "Incident/request kayıtları için REST entegrasyonu.",
    },
    {
        "id": "qdrant",
        "name": "Qdrant / pgvector",
        "category": "Vektör DB",
        "status": "Planlandı",
        "enabled": 0,
        "endpoint": "",
        "description": "Üretimde kalıcı vektör arama katmanı.",
    },
    {
        "id": "sso",
        "name": "Azure AD / Okta SSO",
        "category": "Kimlik",
        "status": "Planlandı",
        "enabled": 0,
        "endpoint": "",
        "description": "OIDC tabanlı kurumsal kimlik ve rol aktarımı.",
    },
]

SLA_MINUTES_BY_PRIORITY = {
    "kritik": 240,
    "urgent": 240,
    "acil": 480,
    "high": 480,
    "normal": 1440,
    "low": 2880,
}


class OpsService:
    def __init__(self, database_path: Path, knowledge_dir: Path) -> None:
        self.database_path = database_path
        self.knowledge_dir = knowledge_dir
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._seed_integrations()

    def create_ticket(self, draft: TicketDraftResponse, requester: str) -> TicketRecord:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        ticket_id = f"KAYRA-{uuid4().hex[:8].upper()}"
        sla_minutes = self._sla_minutes(draft.priority)
        sla_due_at = (now_dt + timedelta(minutes=sla_minutes)).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tickets (
                    id, title, priority, category, summary, status, requester, assignee,
                    resolution_note, sla_minutes, sla_due_at, resolved_at, resolution_minutes,
                    resolution_score, escalation_required, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    draft.title,
                    draft.priority,
                    draft.category,
                    draft.summary,
                    "open",
                    requester,
                    None,
                    None,
                    sla_minutes,
                    sla_due_at,
                    None,
                    None,
                    None,
                    1 if draft.escalation_required else 0,
                    now,
                    now,
                ),
            )
        return self.get_ticket(ticket_id)

    def list_tickets(self, limit: int = 50) -> list[TicketRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._ticket(dict(row)) for row in rows]

    def list_support_tickets(self, limit: int = 80) -> list[TicketRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tickets
                WHERE status NOT IN ('resolved', 'closed')
                ORDER BY
                    CASE priority
                        WHEN 'kritik' THEN 0
                        WHEN 'acil' THEN 1
                        WHEN 'high' THEN 1
                        WHEN 'urgent' THEN 1
                        ELSE 2
                    END,
                    created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._ticket(dict(row)) for row in rows]

    def list_tickets_for_requester(self, requester: str, limit: int = 30) -> list[TicketRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tickets WHERE requester = ? ORDER BY created_at DESC LIMIT ?",
                (requester, limit),
            ).fetchall()
        return [self._ticket(dict(row)) for row in rows]

    def get_ticket(self, ticket_id: str) -> TicketRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not row:
            raise ValueError("Ticket bulunamadı.")
        return self._ticket(dict(row))

    def update_ticket(
        self,
        ticket_id: str,
        *,
        status: str | None = None,
        assignee: str | None = None,
        priority: str | None = None,
        resolution_note: str | None = None,
    ) -> TicketRecord:
        current = self.get_ticket(ticket_id)
        now_dt = datetime.now(timezone.utc)
        resolved_at = current.resolved_at
        resolution_minutes = current.resolution_minutes
        resolution_score = current.resolution_score
        next_status = status or current.status
        if next_status == "resolved" and current.status != "resolved":
            resolved_at = now_dt.isoformat()
            resolution_minutes = self._elapsed_minutes(current.created_at, resolved_at)
            resolution_score = self._resolution_score(current.sla_minutes, resolution_minutes)
        updated = {
            "status": next_status,
            "assignee": assignee if assignee is not None else current.assignee,
            "priority": priority or current.priority,
            "resolution_note": resolution_note if resolution_note is not None else current.resolution_note,
            "resolved_at": resolved_at,
            "resolution_minutes": resolution_minutes,
            "resolution_score": resolution_score,
            "updated_at": now_dt.isoformat(),
            "id": ticket_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tickets
                SET status = ?, assignee = ?, priority = ?, resolution_note = ?, resolved_at = ?,
                    resolution_minutes = ?, resolution_score = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated["status"],
                    updated["assignee"],
                    updated["priority"],
                    updated["resolution_note"],
                    updated["resolved_at"],
                    updated["resolution_minutes"],
                    updated["resolution_score"],
                    updated["updated_at"],
                    updated["id"],
                ),
            )
        return self.get_ticket(ticket_id)

    def list_integrations(self) -> list[IntegrationConfig]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM integrations ORDER BY category, name").fetchall()
        return [self._integration(dict(row)) for row in rows]

    def update_integration(
        self,
        integration_id: str,
        *,
        status: str | None = None,
        enabled: bool | None = None,
        endpoint: str | None = None,
    ) -> IntegrationConfig:
        current = self.get_integration(integration_id)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE integrations
                SET status = ?, enabled = ?, endpoint = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status or current.status,
                    int(current.enabled if enabled is None else enabled),
                    endpoint if endpoint is not None else current.endpoint,
                    datetime.now(timezone.utc).isoformat(),
                    integration_id,
                ),
            )
        return self.get_integration(integration_id)

    def get_integration(self, integration_id: str) -> IntegrationConfig:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM integrations WHERE id = ?", (integration_id,)).fetchone()
        if not row:
            raise ValueError("Entegrasyon bulunamadı.")
        return self._integration(dict(row))

    def list_documents(self) -> list[KnowledgeDocumentInfo]:
        docs: list[KnowledgeDocumentInfo] = []
        if not self.knowledge_dir.exists():
            return docs
        for path in sorted(self.knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = self._extract_title(text, path)
            category = self._extract_category(text)
            stat = path.stat()
            docs.append(
                KnowledgeDocumentInfo(
                    filename=path.name,
                    title=title,
                    category=category,
                    size=stat.st_size,
                    updated_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
            )
        return docs

    def delete_document(self, filename: str) -> None:
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "", filename)
        path = self.knowledge_dir / safe
        if path.suffix.lower() != ".md" or not path.exists() or not path.is_file():
            raise ValueError("Doküman bulunamadı.")
        path.unlink()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    category TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    assignee TEXT,
                    resolution_note TEXT,
                    sla_minutes INTEGER,
                    sla_due_at TEXT,
                    resolved_at TEXT,
                    resolution_minutes INTEGER,
                    resolution_score INTEGER,
                    escalation_required INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "tickets", "resolution_note", "TEXT")
            self._ensure_column(conn, "tickets", "sla_minutes", "INTEGER")
            self._ensure_column(conn, "tickets", "sla_due_at", "TEXT")
            self._ensure_column(conn, "tickets", "resolved_at", "TEXT")
            self._ensure_column(conn, "tickets", "resolution_minutes", "INTEGER")
            self._ensure_column(conn, "tickets", "resolution_score", "INTEGER")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS integrations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    endpoint TEXT,
                    description TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _seed_integrations(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for item in DEFAULT_INTEGRATIONS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO integrations (
                        id, name, category, status, enabled, endpoint, description, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["id"],
                        item["name"],
                        item["category"],
                        item["status"],
                        item["enabled"],
                        item["endpoint"],
                        item["description"],
                        now,
                    ),
                )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ticket(self, row: dict) -> TicketRecord:
        sla_minutes = int(row.get("sla_minutes") or self._sla_minutes(row["priority"]))
        sla_due_at = row.get("sla_due_at") or self._due_at(row["created_at"], sla_minutes)
        resolved_at = row.get("resolved_at")
        resolution_minutes = row.get("resolution_minutes")
        if resolution_minutes is None and resolved_at:
            resolution_minutes = self._elapsed_minutes(row["created_at"], resolved_at)
        resolution_score = row.get("resolution_score")
        if resolution_score is None and resolution_minutes is not None:
            resolution_score = self._resolution_score(sla_minutes, int(resolution_minutes))
        return TicketRecord(
            id=row["id"],
            title=row["title"],
            priority=row["priority"],
            category=row["category"],
            summary=row["summary"],
            status=row["status"],
            requester=row["requester"],
            assignee=row.get("assignee"),
            resolution_note=row.get("resolution_note"),
            sla_minutes=sla_minutes,
            sla_due_at=sla_due_at,
            sla_status=self._sla_status(row["status"], sla_due_at),
            resolved_at=resolved_at,
            resolution_minutes=resolution_minutes,
            resolution_score=resolution_score,
            escalation_required=bool(row["escalation_required"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _sla_minutes(self, priority: str) -> int:
        return SLA_MINUTES_BY_PRIORITY.get(priority.strip().lower(), SLA_MINUTES_BY_PRIORITY["normal"])

    def _due_at(self, created_at: str, sla_minutes: int) -> str:
        return (datetime.fromisoformat(created_at) + timedelta(minutes=sla_minutes)).isoformat()

    def _elapsed_minutes(self, start_at: str, end_at: str) -> int:
        start = datetime.fromisoformat(start_at)
        end = datetime.fromisoformat(end_at)
        return max(0, int((end - start).total_seconds() // 60))

    def _resolution_score(self, sla_minutes: int, resolution_minutes: int) -> int:
        if resolution_minutes <= sla_minutes:
            ratio = resolution_minutes / max(sla_minutes, 1)
            return max(85, min(100, 100 - int(ratio * 10)))
        overdue_ratio = (resolution_minutes - sla_minutes) / max(sla_minutes, 1)
        return max(40, 80 - int(overdue_ratio * 35))

    def _sla_status(self, status: str, sla_due_at: str) -> str:
        if status == "resolved":
            return "met"
        due_at = datetime.fromisoformat(sla_due_at)
        return "breached" if datetime.now(timezone.utc) > due_at else "active"

    def _integration(self, row: dict) -> IntegrationConfig:
        return IntegrationConfig(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            status=row["status"],
            enabled=bool(row["enabled"]),
            endpoint=row.get("endpoint"),
            description=row["description"],
            updated_at=row["updated_at"],
        )

    def _extract_title(self, text: str, path: Path) -> str:
        match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
        return match.group(1).strip() if match else path.stem.replace("_", " ").title()

    def _extract_category(self, text: str) -> str:
        match = re.search(r"^Kategori:\s*(.+)$", text, flags=re.MULTILINE)
        return match.group(1).strip() if match else "Bilgi Tabanı"
