import re
from typing import List, Dict, Any


def chunk_text_by_tokens(
    text: str,
    page_number: int,
    chunk_size_tokens: int = 500,
    chunk_overlap_tokens: int = 50
) -> List[Dict[str, Any]]:
    """
    Splits text into chunks of approximately chunk_size_tokens (words/tokens)
    with chunk_overlap_tokens overlap, preserving page_number provenance.
    """
    if not text or not text.strip():
        return []

    # Tokenize text by words/whitespace
    words = re.findall(r"\S+", text)
    if not words:
        return []

    chunks = []
    chunk_index = 0
    step = chunk_size_tokens - chunk_overlap_tokens
    if step <= 0:
        step = chunk_size_tokens

    for start in range(0, len(words), step):
        end = min(start + chunk_size_tokens, len(words))
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words)

        chunks.append({
            "page_number": page_number,
            "chunk_index": chunk_index,
            "chunk_text": chunk_str,
            "token_count": len(chunk_words)
        })
        chunk_index += 1

        if end >= len(words):
            break

    return chunks
