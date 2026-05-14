from __future__ import annotations

from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

from app.schemas import Source


class OnlineSearchService:
    def search(self, query: str, limit: int = 3) -> list[Source]:
        params = urlencode(
            {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
            }
        )
        request = Request(
            f"https://api.duckduckgo.com/?{params}",
            headers={"User-Agent": "KayraEnterpriseAssistant/0.3"},
        )
        try:
            with urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        results: list[Source] = []
        abstract = payload.get("AbstractText")
        abstract_url = payload.get("AbstractURL") or "https://duckduckgo.com/"
        heading = payload.get("Heading") or "Online kaynak"
        if abstract:
            results.append(
                Source(
                    title=f"Online: {heading}",
                    path=abstract_url,
                    score=1.0,
                    excerpt=abstract[:360],
                )
            )

        for topic in payload.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            if "Text" not in topic:
                continue
            results.append(
                Source(
                    title="Online ilgili sonuç",
                    path=topic.get("FirstURL") or "https://duckduckgo.com/",
                    score=0.72,
                    excerpt=topic["Text"][:360],
                )
            )
        return results[:limit]
