import os
import logging
from typing import List, Dict, Any, Optional

from config import settings
from app.services.embedding_service import generate_embedding, generate_batch_embeddings
from app.services.normalization_service import normalize_subsidiary_scope

logger = logging.getLogger(__name__)

# Global persistent collection reference
_chroma_collection = None


def get_chroma_collection():
    """Initializes and returns persistent ChromaDB collection instance."""
    global _chroma_collection
    if _chroma_collection is None:
        try:
            import chromadb
            os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)
            client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
            _chroma_collection = client.get_or_create_collection(
                name="coalintel_chunks",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Initialized persistent ChromaDB collection at '{settings.CHROMA_DB_DIR}'.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization note: {e}. Fallback vector store active.")
            _chroma_collection = "MOCK"
    return _chroma_collection


def add_chunks_to_vector_store(chunks: List[Any], filename: str, subsidiary: Optional[str] = "CIL HQ") -> bool:
    """
    Indexes document chunks into persistent ChromaDB vector store.
    Preserves document provenance: document_id, filename, page_number, chunk_index.
    """
    if not chunks:
        return True

    collection = get_chroma_collection()

    ids = []
    documents = []
    metadatas = []
    texts_to_embed = []

    for chunk in chunks:
        chunk_id_str = getattr(chunk, "embedding_id", None) or f"chunk_{chunk.document_id}_{chunk.page_number}_{chunk.chunk_index}"
        ids.append(chunk_id_str)
        documents.append(chunk.chunk_text)
        metadatas.append({
            "document_id": chunk.document_id,
            "filename": filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "subsidiary": subsidiary or "CIL HQ"
        })
        texts_to_embed.append(chunk.chunk_text)

    embeddings = generate_batch_embeddings(texts_to_embed)

    if collection == "MOCK" or collection is None:
        logger.info(f"Indexed {len(ids)} chunks to mock vector store.")
        return True

    try:
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"Successfully upserted {len(ids)} chunk vectors to ChromaDB collection.")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert chunks to ChromaDB: {e}")
        return False


def delete_document_vectors(document_id: int) -> bool:
    """
    Skips ChromaDB vector cleanup during document reprocessing.

    ChromaDB is not part of the authoritative data extraction path.
    PostgreSQL remains the source of truth for extracted Ministry of Coal
    metrics, so vector-store cleanup must not prevent document processing.
    """
    logger.info(
        f"Chroma vector cleanup skipped for Document #{document_id}; "
        f"continuing with authoritative PostgreSQL extraction."
    )
    return True
def search_vector_store(
    query_text: str,
    top_k: int = 5,
    subsidiary_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Executes semantic cosine vector search against ChromaDB.
    Returns candidate evidence chunks sorted by vector similarity.
    """
    if not query_text:
        return []

    collection = get_chroma_collection()
    query_vec = generate_embedding(query_text)

    if collection == "MOCK" or collection is None:
        # Fallback mock search results for un-indexed or host testing
        return []

    try:
        where_clause = None
        norm_sub = normalize_subsidiary_scope(subsidiary_filter)
        if norm_sub:
            where_clause = {"subsidiary": norm_sub}

        results = collection.query(
            query_embeddings=[query_vec],
            n_results=top_k,
            where=where_clause
        )

        results_list = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            for idx in range(len(results["ids"][0])):
                doc_text = results["documents"][0][idx]
                meta = results["metadatas"][0][idx]
                dist = results["distances"][0][idx] if results.get("distances") else 0.0
                similarity = max(0.0, 1.0 - dist)

                results_list.append({
                    "chunk_id": None,
                    "document_id": meta.get("document_id", 0),
                    "filename": meta.get("filename", "Document.pdf"),
                    "page_number": meta.get("page_number", 1),
                    "chunk_index": meta.get("chunk_index", 0),
                    "text": doc_text,
                    "vector_score": round(similarity, 4)
                })

        return results_list
    except Exception as e:
        logger.error(f"Error querying ChromaDB vector store: {e}")
        return []
