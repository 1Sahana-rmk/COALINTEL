from app.services.document_ai_client import DocumentAIClient


def test_document_ai_client_accepts_render_private_hostport():
    client = DocumentAIClient(base_url="coalintel-document-ai:10000")

    assert client.base_url == "http://coalintel-document-ai:10000"


def test_document_ai_client_preserves_local_http_url():
    client = DocumentAIClient(base_url="http://127.0.0.1:8765/")

    assert client.base_url == "http://127.0.0.1:8765"
