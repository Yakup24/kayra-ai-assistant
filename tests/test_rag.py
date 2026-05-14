from pathlib import Path

from app.services.rag import KnowledgeBase, tokenize


def test_tokenize_supports_turkish_characters():
    tokens = tokenize("İade süreci nasıl işliyor?")
    assert "iade" in tokens
    assert "süreci" in tokens
    assert "sureci" in tokens


def test_knowledge_base_finds_relevant_document():
    kb = KnowledgeBase(Path("data/knowledge"))
    results = kb.search("İade talebi kaç gün içinde yapılır?")
    assert results
    assert "E-Ticaret" in results[0].chunk.title
