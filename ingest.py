"""CLI entry point for policy ingestion/indexing."""

from rag_pipeline import PolicyRAG


if __name__ == "__main__":
    result = PolicyRAG().build()
    print(f"Indexed {result['documents']} policy documents into {result['chunks']} chunks.")
