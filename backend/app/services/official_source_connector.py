"""Bounded, same-host official-source discovery and download abstractions."""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urldefrag, urljoin, urlparse


@dataclass
class DiscoveredDocument:
    source: str
    category: Optional[str]
    title: Optional[str]
    url: str
    discovered_at: datetime
    publication_date: Optional[datetime] = None


@dataclass
class DiscoveryResult:
    documents: List[DiscoveredDocument] = field(default_factory=list)
    pages_checked: int = 0
    page_failures: List[Dict[str, str]] = field(default_factory=list)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: List[Dict[str, str]] = []
        self._href: Optional[str] = None
        self._text: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            self.links.append({"href": self._href, "text": " ".join(self._text).strip()})
            self._href = None
            self._text = []


class OfficialSourceConnector:
    allowed_extensions = {".pdf", ".docx", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    retryable_statuses = {429, 500, 502, 503, 504}

    def __init__(self, base_url: str, organization: str, *, client: Any = None, max_documents: int = 100,
                 max_category_pages: int = 25, max_attempts: int = 3, backoff_factor: float = 0.25,
                 sleep: Callable[[float], None] = time.sleep):
        self.base_url = base_url
        self.organization = organization
        self.client = client
        self.max_documents = max_documents
        self.max_category_pages = max_category_pages
        self.max_attempts = max(1, max_attempts)
        self.backoff_factor = max(0.0, backoff_factor)
        self.sleep = sleep
        self.last_discovery = DiscoveryResult()
        root = urlparse(base_url).netloc.lower()
        self.allowed_hosts = {root, root.removeprefix("www.")}

    def _client(self):
        if self.client is not None:
            return self.client
        import httpx
        self.client = httpx.Client(timeout=httpx.Timeout(20.0, connect=10.0), follow_redirects=True,
                                    headers={"User-Agent": "COALINTEL-official-sync/1.0"})
        return self.client

    def close(self):
        if self.client is not None and hasattr(self.client, "close"):
            self.client.close()

    def _is_allowed_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in self.allowed_hosts

    def _canonical_url(self, url: str, base: str) -> str:
        return urldefrag(urljoin(base, url))[0]

    def _request(self, url: str):
        if not self._is_allowed_url(url):
            raise ValueError("Refusing to request a URL outside the configured official source host")
        client = self._client()
        for attempt in range(self.max_attempts):
            try:
                try:
                    response = client.get(url, timeout=20.0)
                except TypeError:
                    response = client.get(url)
                final_url = str(getattr(response, "url", None) or url)
                if not self._is_allowed_url(final_url):
                    raise ValueError("Official source redirected outside the configured host")
                status_code = int(getattr(response, "status_code", 200))
                if status_code in self.retryable_statuses and attempt + 1 < self.max_attempts:
                    delay = self.backoff_factor * (2 ** attempt)
                    try:
                        delay = max(delay, min(float(response.headers.get("retry-after", 0)), 10.0))
                    except (AttributeError, TypeError, ValueError):
                        pass
                    self.sleep(delay)
                    continue
                response.raise_for_status()
                return response
            except ValueError:
                raise
            except Exception as exc:
                retryable = exc.__class__.__module__.startswith("httpx") and any(
                    token in exc.__class__.__name__ for token in ("Timeout", "Network", "Connect")
                )
                if not retryable or attempt + 1 >= self.max_attempts:
                    raise
                self.sleep(self.backoff_factor * (2 ** attempt))
        raise RuntimeError("Official source request failed")

    def _is_category_page(self, url: str) -> bool:
        path = urlparse(url).path.lower().rstrip("/")
        return path.startswith("/major-statistics") or path.startswith("/public-information") or path == urlparse(self.base_url).path.lower().rstrip("/")

    def _category(self, url: str, parent_title: Optional[str] = None) -> Optional[str]:
        if parent_title:
            return parent_title[:200]
        parts = [p.replace("-", " ").replace("_", " ").strip() for p in urlparse(url).path.split("/") if p.strip()]
        return parts[-2].title() if len(parts) > 1 else None

    def discover_documents_with_report(self) -> DiscoveryResult:
        result = DiscoveryResult()
        queue = [self.base_url]
        visited, seen_documents = set(), set()
        while queue and len(visited) < self.max_category_pages and len(result.documents) < self.max_documents:
            page_url = self._canonical_url(queue.pop(0), self.base_url)
            if page_url in visited or not self._is_allowed_url(page_url):
                continue
            visited.add(page_url)
            try:
                response = self._request(page_url)
                parser = _LinkParser()
                parser.feed(response.text)
                result.pages_checked += 1
            except Exception as exc:
                result.page_failures.append({"url": page_url, "error": str(exc)[:500]})
                continue
            for link in parser.links:
                url = self._canonical_url(link["href"], page_url)
                if not self._is_allowed_url(url):
                    continue
                filename = urlparse(url).path.rsplit("/", 1)[-1]
                extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
                if extension in self.allowed_extensions:
                    if url in seen_documents:
                        continue
                    seen_documents.add(url)
                    result.documents.append(DiscoveredDocument(source=self.organization,
                        category=self._category(page_url, link["text"] or None), title=link["text"] or filename,
                        url=url, discovered_at=datetime.now(timezone.utc)))
                    if len(result.documents) >= self.max_documents:
                        break
                elif self._is_category_page(url) and url not in visited and url not in queue:
                    queue.append(url)
        self.last_discovery = result
        return result

    def discover_documents(self) -> List[DiscoveredDocument]:
        return self.discover_documents_with_report().documents

    def download_document(self, document: DiscoveredDocument, *, max_bytes: int = 50 * 1024 * 1024) -> bytes:
        if not self._is_allowed_url(document.url):
            raise ValueError("Refusing to download a URL outside the configured official source host")
        response = self._request(document.url)
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            raise ValueError("Official document exceeds the configured size limit")
        content = response.content
        if len(content) > max_bytes:
            raise ValueError("Official document exceeds the configured size limit")
        return content

    def extract_source_metadata(self, document: DiscoveredDocument) -> Dict[str, Any]:
        return {"source_organization": self.organization, "title": document.title, "category": document.category, "publication_date": document.publication_date}

    def check_for_updates(self, document: DiscoveredDocument, previous_checksum: Optional[str]) -> str:
        checksum = hashlib.sha256(self.download_document(document)).hexdigest()
        return "UNCHANGED" if checksum == previous_checksum else ("UPDATED" if previous_checksum else "NEW")


class MinistryOfCoalConnector(OfficialSourceConnector):
    def __init__(self, *, client: Any = None, max_documents: int = 100, **kwargs):
        super().__init__("https://coal.nic.in/major-statistics-page", "Ministry of Coal", client=client, max_documents=max_documents, **kwargs)
