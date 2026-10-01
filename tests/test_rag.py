from rag_pipeline import PolicyRAG


def test_policy_corpus_has_multiple_documents():
    rag = PolicyRAG()
    assert len(set(chunk.document_id for chunk in rag.chunks)) >= 8


def test_rag_returns_citation_metadata():
    rag = PolicyRAG()
    results = rag.search("PTO manager approval notice", k=3)
    assert results
    assert all("document_id" in result and "section" in result and "snippet" in result for result in results)
