import os
import re
import abc
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from config import settings
from app.services.normalization_service import (
    KNOWN_MINES,
    GENERIC_MINE_PHRASES,
    get_base_mine_name,
    detect_query_fiscal_year,
    chunk_has_metric_for_entity,
    classify_document_authority,
    is_historical_evidence_snippet,
    is_corporate_context_snippet,
)
from app.services.hybrid_search_service import detect_query_entities

logger = logging.getLogger(__name__)


class BaseLLMProvider(abc.ABC):
    """
    Abstract Base Class for COALINTEL LLM Providers.
    Ensures backend vendor-independence between Gemini, OpenAI, or Degraded Mode.
    """
    provider_name: str = "base"

    @abc.abstractmethod
    def generate(self, prompt: str) -> str:
        """Generates answer string given XML-isolated prompt."""
        pass

    @abc.abstractmethod
    def generate_completion(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate completion given user query prompt and isolated context chunks.
        """
        pass

    @abc.abstractmethod
    def generate_general_ai(self, query: str) -> Dict[str, Any]:
        """
        Generates direct response for general conceptual, coding, or conversational inquiries.
        """
        pass


class DegradedLLMProvider(BaseLLMProvider):
    """
    Fallback Provider used when no LLM API key is present or LLM API times out.
    Returns grounded evidence citations without inventing content.
    """
    provider_name: str = "degraded"

    @staticmethod
    def _parse_structured_chunk(chunk_text: str) -> Optional[Dict[str, Any]]:
        """Extracts structured metric fields from chunk text if present."""
        if "mine entity:" not in chunk_text.lower() and "metric:" not in chunk_text.lower():
            return None

        mine_m = re.search(r"Mine Entity:\s*([^\|\n]+)", chunk_text, re.IGNORECASE)
        metric_m = re.search(r"Metric:\s*([^\|\n]+)", chunk_text, re.IGNORECASE)
        raw_val_m = re.search(r"Raw Extracted Value:\s*([^\|\n]+)", chunk_text, re.IGNORECASE)
        norm_val_m = re.search(r"Normalized Value:\s*([^\|\n]+)", chunk_text, re.IGNORECASE)
        fy_m = re.search(r"Fiscal Year:\s*([^\|\n]+)", chunk_text, re.IGNORECASE)
        snippet_m = re.search(r"Raw Evidence Snippet:\s*(.+)", chunk_text, re.DOTALL | re.IGNORECASE)

        mine_name = mine_m.group(1).strip() if mine_m else None
        metric_name = metric_m.group(1).strip() if metric_m else "Production"
        raw_val = raw_val_m.group(1).strip() if raw_val_m else None
        norm_val = norm_val_m.group(1).strip() if norm_val_m else None
        fy = fy_m.group(1).strip() if fy_m else "FY 2023-24"
        snippet = snippet_m.group(1).strip() if snippet_m else ""

        if raw_val and norm_val and raw_val.lower() != norm_val.lower() and not raw_val.upper().endswith("MT"):
            val_display = f"{raw_val} ({norm_val})"
        elif norm_val:
            val_display = norm_val
        elif raw_val:
            val_display = raw_val
        else:
            val_display = None

        return {
            "mine_name": mine_name,
            "metric_name": metric_name,
            "value": val_display,
            "fiscal_year": fy,
            "snippet": snippet
        }

    def generate(self, prompt: str) -> str:
        """Grounded synthesis of XML context for degraded/local execution."""
        # Extract untrusted context block strictly within XML boundary delimiters
        ctx_match = re.search(r"<untrusted_document_context>\s*(.*?)\s*</untrusted_document_context>", prompt, re.DOTALL)
        if not ctx_match:
            return "Insufficient evidence found for this query."
        context_str = ctx_match.group(1).strip()

        if not context_str or "Insufficient evidence" in context_str:
            return "Insufficient evidence found for this query."

        # Parse retrieved evidence chunks strictly from context_str using canonical citation tag headers
        chunk_pattern = re.compile(
            r"\[([A-Za-z0-9_\-\.]+),\s*Page\s*(\d+)\]\s*\n(.*?)(?=(?:\[[A-Za-z0-9_\-\.]+\,\s*Page\s*\d+\])|\Z)",
            re.DOTALL
        )
        parsed_chunks = []
        for match in chunk_pattern.finditer(context_str):
            parsed_chunks.append({
                "filename": match.group(1),
                "page_number": int(match.group(2)),
                "tag": f"[{match.group(1)}, Page {match.group(2)}]",
                "text": match.group(3).strip()
            })

        if not parsed_chunks:
            return "Insufficient evidence found for this query."

        # Extract user query
        q_match = re.search(r"USER QUESTION:\s*(.*?)(?:\n|$)", prompt)
        user_query = q_match.group(1).strip() if q_match else prompt
        q_lower = user_query.lower()

        # Target mine, temporal scope, and fiscal year detection using canonical entity parsing
        q_entities = detect_query_entities(user_query)
        target_mines = q_entities.get("mines", [])
        target_mine = target_mines[0] if target_mines else None
        base_mine = get_base_mine_name(target_mine) if target_mine else None
        target_fy = q_entities.get("fiscal_year") or detect_query_fiscal_year(user_query)

        # Detect target metric and metric domain
        metric_domain = q_entities.get("metric_domain")
        target_metric = q_entities.get("metric")
        is_corporate = q_entities.get("is_corporate_query", False)

        if target_mine:
            mine_in_context = target_mine.lower() in context_str.lower() or (base_mine and base_mine.lower() in context_str.lower())
            if not mine_in_context:
                return "Insufficient evidence found for this query."

        # Filter candidate chunks to those that actually provide evidence for queried entity & metric domain
        matching_chunks = []
        for c in parsed_chunks:
            if chunk_has_metric_for_entity(
                c["text"],
                target_mines=[target_mine] if target_mine else None,
                metric_domain=metric_domain,
                target_metric=target_metric
            ):
                matching_chunks.append(c)

        if not matching_chunks and target_mine:
            return "Insufficient evidence found for this query."

        candidate_chunks = matching_chunks if matching_chunks else parsed_chunks

        # Disqualify candidate chunks that are historical inception context when answering modern FY queries
        if target_fy:
            non_historical = [
                c for c in candidate_chunks
                if not is_historical_evidence_snippet(c["text"], target_fy=target_fy)
            ]
            if non_historical:
                candidate_chunks = non_historical
            else:
                return "Insufficient evidence found for this query."

        # Authority sorting: prioritize OFFICIAL over SYNTHETIC_TEST unless explicit test query
        is_explicit_test_query = any(w in q_lower for w in ["synthetic", "mock", "test data", "demo data"])
        if not is_explicit_test_query and candidate_chunks:
            candidate_chunks = sorted(
                candidate_chunks,
                key=lambda c: 0 if classify_document_authority(c.get("filename", "")) == "OFFICIAL" else (
                    1 if classify_document_authority(c.get("filename", "")) != "SYNTHETIC_TEST" else 2
                )
            )

        # Check if comparison query
        is_comparison = "compare" in q_lower or "versus" in q_lower or "vs" in q_lower
        if is_comparison and len(candidate_chunks) >= 2:
            ans_parts = ["According to ingested document evidence:"]
            for c in candidate_chunks:
                s_info = self._parse_structured_chunk(c["text"])
                if s_info and s_info["value"]:
                    m_label = s_info["mine_name"]
                    if not m_label or m_label == "Unspecified Mine":
                        sub_m = re.search(r"\b([A-Z]{3,4})\b", c["filename"] + " " + c["text"])
                        m_label = f"{sub_m.group(1)} Total" if sub_m else "Total"
                    ans_parts.append(f"- {m_label} {s_info['metric_name']}: {s_info['value']} {c['tag']}")
                else:
                    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", c["text"]) if s.strip()]
                    rel_s = sentences[0] if sentences else c["text"][:120]
                    ans_parts.append(f"- {rel_s} {c['tag']}")
            return "\n".join(ans_parts)

        # Find best matching chunk for target mine or general query
        best_chunk = None
        if target_mine:
            mine_terms = [target_mine.lower()]
            if base_mine and len(base_mine) >= 3 and base_mine.lower() not in mine_terms:
                mine_terms.append(base_mine.lower())

            # 1. Look for chunk where structured mine_name matches target mine or base mine
            for c in candidate_chunks:
                s_info = self._parse_structured_chunk(c["text"])
                if s_info and s_info["mine_name"]:
                    m_lower = s_info["mine_name"].lower()
                    m_base = get_base_mine_name(s_info["mine_name"]).lower()
                    if any(mt in m_lower or mt in m_base for mt in mine_terms):
                        best_chunk = c
                        break
            # 2. Look for chunk where raw evidence snippet explicitly contains target mine or base mine
            if not best_chunk:
                for c in candidate_chunks:
                    t_lower = c["text"].lower()
                    snippet_part = t_lower.split("raw evidence snippet:")[-1] if "raw evidence snippet:" in t_lower else t_lower
                    if any(mt in snippet_part for mt in mine_terms):
                        best_chunk = c
                        break
            # 3. Check any chunk containing target mine or base mine
            if not best_chunk:
                for c in candidate_chunks:
                    t_lower = c["text"].lower()
                    if any(mt in t_lower for mt in mine_terms):
                        best_chunk = c
                        break
        else:
            if is_corporate:
                def score_corporate_chunk(c):
                    t = c["text"].lower()
                    score = 0
                    if is_corporate_context_snippet(c["text"]):
                        score += 15
                    if "cil" in t or "coal india" in t:
                        score += 8
                    if target_fy and (target_fy in t or target_fy[-5:] in t):
                        score += 6
                    if "total" in t or "as a whole" in t or "all subsidiaries" in t:
                        score += 4
                    # Demote individual subsidiary mines for corporate query
                    if any(km.lower() in t for km in KNOWN_MINES):
                        score -= 5
                    return score

                sorted_corp = sorted(candidate_chunks, key=score_corporate_chunk, reverse=True)
                if sorted_corp and score_corporate_chunk(sorted_corp[0]) > 0:
                    best_chunk = sorted_corp[0]
                else:
                    return "Insufficient evidence found for this query."
            else:
                # Check if query asks for aggregate/total
                if "total" in q_lower:
                    for c in candidate_chunks:
                        if "total" in c["text"].lower() or "as a whole" in c["text"].lower():
                            best_chunk = c
                            break
                if not best_chunk:
                    best_chunk = candidate_chunks[0]

        if not best_chunk:
            return "Insufficient evidence found for this query."

        tag = best_chunk["tag"]
        chunk_text = best_chunk["text"]

        # 1. Dynamic synthesis from structured metric evidence
        s_info = self._parse_structured_chunk(chunk_text)
        if s_info and s_info["value"]:
            m_name = s_info["mine_name"]
            m_metric = s_info["metric_name"]
            m_val = s_info["value"]
            m_fy = s_info["fiscal_year"]

            # Grounded entity naming: only use "CIL" if evidence chunk actually supports corporate context or entity is CIL Corporate
            if is_corporate_context_snippet(chunk_text) or (m_name and m_name.lower() in ["cil corporate", "cil"]):
                entity_display = "CIL"
            elif not m_name or m_name.lower() in GENERIC_MINE_PHRASES:
                sub_m = re.search(r"\b([A-Z]{3,4})\b", best_chunk["filename"] + " " + chunk_text)
                entity_display = f"{sub_m.group(1)} total" if sub_m else "Total"
            else:
                entity_display = m_name

            return f"According to ingested document evidence {tag}, {entity_display} {m_metric.lower()} was {m_val} in {m_fy}."

        # 2. Dynamic synthesis from unstructured text chunk
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", chunk_text) if s.strip()]
        relevant_sentence = None
        if target_mine:
            mine_terms = [target_mine.lower()]
            if base_mine and len(base_mine) >= 3 and base_mine.lower() not in mine_terms:
                mine_terms.append(base_mine.lower())

            # A. First look for sentence mentioning target mine AND target metric AND numbers/units
            for s in sentences:
                s_lower = s.lower()
                has_m = any(mt in s_lower for mt in mine_terms)
                has_met = chunk_has_metric_for_entity(
                    s,
                    target_mines=[target_mine],
                    metric_domain=metric_domain,
                    target_metric=target_metric
                )
                if has_m and has_met and re.search(r"\d+(?:\.\d+)?\s*(?:MT|Lakh|Million|Tonnes|M\.Cu\.M|MCuM|%|cum)", s, re.IGNORECASE):
                    # If target_fy is specified, prioritize sentence with matching temporal token
                    if target_fy:
                        fy_short = target_fy[-5:]  # e.g. 23-24
                        if target_fy in s or fy_short in s:
                            relevant_sentence = s
                            break
                    if not relevant_sentence:
                        relevant_sentence = s

            # B. If not found, look for any sentence mentioning target/base mine AND target metric
            if not relevant_sentence:
                for s in sentences:
                    s_lower = s.lower()
                    if any(mt in s_lower for mt in mine_terms) and chunk_has_metric_for_entity(
                        s,
                        target_mines=[target_mine],
                        metric_domain=metric_domain,
                        target_metric=target_metric
                    ):
                        relevant_sentence = s
                        break
        else:
            # Generic query (no target mine): pick sentence matching metric and numbers
            for s in sentences:
                if target_fy and is_historical_evidence_snippet(s, target_fy=target_fy):
                    continue
                has_met = chunk_has_metric_for_entity(
                    s,
                    metric_domain=metric_domain,
                    target_metric=target_metric
                )
                if has_met and re.search(r"\d+(?:\.\d+)?\s*(?:MT|Lakh|Million|Tonnes|M\.Cu\.M|MCuM|%|cum)", s, re.IGNORECASE):
                    if target_fy and (target_fy in s or target_fy[-5:] in s):
                        relevant_sentence = s
                        break
                    if not relevant_sentence:
                        relevant_sentence = s
            if not relevant_sentence and sentences:
                for s in sentences:
                    if target_fy and is_historical_evidence_snippet(s, target_fy=target_fy):
                        continue
                    if chunk_has_metric_for_entity(s, metric_domain=metric_domain, target_metric=target_metric):
                        relevant_sentence = s
                        break

        if relevant_sentence:
            return f"According to ingested document evidence {tag}: \"{relevant_sentence}\""

        return "Insufficient evidence found for this query."

    def generate_completion(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        answer_text = self.generate(prompt)
        citations = []
        for c in context_chunks:
            fname = c.get("filename", "Document.pdf")
            pnum = c.get("page_number", 1)
            citations.append({
                "document_name": fname,
                "page_number": pnum,
                "citation_tag": f"[{fname}, Page {pnum}]"
            })
        return {
            "answer": answer_text,
            "citations": citations,
            "degraded_mode": True,
            "provider": "degraded"
        }

    def generate_general_ai(self, query: str) -> Dict[str, Any]:
        """
        Generates deterministic local responses for general conceptual, coding, and chat queries.
        """
        q_clean = query.strip()
        q_lower = q_clean.lower()

        # 1. Conversational greetings
        if any(q_lower == g or q_lower.startswith(g + " ") for g in ["hi", "hello", "hey", "greetings"]):
            answer = "Hello! I am COALINTEL AI Assistant, ready to assist you with geological analytics, coal production metrics, and general technical inquiries."
        elif "how are you" in q_lower:
            answer = "I am COALINTEL AI Assistant, operating normally and ready to help with mining intelligence, document extractions, or general technical questions."
        elif "what are you doing" in q_lower or "what can you do" in q_lower:
            answer = "I am COALINTEL AI, processing geological data, validating multi-source mining metrics, and answering general technical and mining questions."
        
        # 2. Programming / Coding queries
        elif "calculator" in q_lower and ("python" in q_lower or "code" in q_lower or True):
            answer = (
                "Here is a complete, interactive command-line Calculator implemented in Python:\n\n"
                "```python\n"
                "def calculate(num1: float, op: str, num2: float) -> float:\n"
                "    if op == '+':\n"
                "        return num1 + num2\n"
                "    elif op == '-':\n"
                "        return num1 - num2\n"
                "    elif op == '*':\n"
                "        return num1 * num2\n"
                "    elif op == '/':\n"
                "        if num2 == 0:\n"
                "            raise ZeroDivisionError(\"Cannot divide by zero.\")\n"
                "        return num1 / num2\n"
                "    else:\n"
                "        raise ValueError(f\"Unsupported operator: {op}\")\n\n"
                "# Example interactive calculator\n"
                "if __name__ == '__main__':\n"
                "    print(\"COALINTEL Python Calculator\")\n"
                "    try:\n"
                "        a = float(input(\"Enter first number: \"))\n"
                "        operator = input(\"Enter operator (+, -, *, /): \").strip()\n"
                "        b = float(input(\"Enter second number: \"))\n"
                "        result = calculate(a, operator, b)\n"
                "        print(f\"Result: {a} {operator} {b} = {result}\")\n"
                "    except Exception as e:\n"
                "        print(f\"Error: {e}\")\n"
                "```"
            )
        elif "factorial" in q_lower:
            answer = (
                "Here is how to calculate Factorial in Python both iteratively and recursively:\n\n"
                "```python\n"
                "# 1. Recursive approach\n"
                "def factorial_recursive(n: int) -> int:\n"
                "    if n < 0:\n"
                "        raise ValueError(\"Factorial is not defined for negative numbers.\")\n"
                "    if n <= 1:\n"
                "        return 1\n"
                "    return n * factorial_recursive(n - 1)\n\n"
                "# 2. Iterative approach\n"
                "def factorial_iterative(n: int) -> int:\n"
                "    result = 1\n"
                "    for i in range(2, n + 1):\n"
                "        result *= i\n"
                "    return result\n\n"
                "# Example:\n"
                "print(factorial_recursive(5))  # Output: 120\n"
                "```"
            )
        elif "reverse a string" in q_lower:
            answer = (
                "Here is how to reverse a string in Python using slicing:\n\n"
                "```python\n"
                "def reverse_string(s: str) -> str:\n"
                "    return s[::-1]\n\n"
                "# Example usage:\n"
                "original = \"COALINTEL\"\n"
                "reversed_text = reverse_string(original)\n"
                "print(reversed_text)  # Output: LETNILAOC\n"
                "```"
            )
        elif "binary tree" in q_lower:
            answer = (
                "A Binary Tree is a non-linear hierarchical data structure in which each node has at most two children, referred to as the left child and the right child.\n\n"
                "Here is a standard Python implementation:\n\n"
                "```python\n"
                "class TreeNode:\n"
                "    def __init__(self, val=0, left=None, right=None):\n"
                "        self.val = val\n"
                "        self.left = left\n"
                "        self.right = right\n\n"
                "def inorder_traversal(root: TreeNode):\n"
                "    if root:\n"
                "        inorder_traversal(root.left)\n"
                "        print(root.val, end=' ')\n"
                "        inorder_traversal(root.right)\n"
                "```"
            )
        elif "binary search" in q_lower:
            answer = (
                "Binary Search is an $O(\\log n)$ divide-and-conquer algorithm to find the position of a target value within a sorted array.\n\n"
                "```python\n"
                "def binary_search(arr: list[int], target: int) -> int:\n"
                "    left, right = 0, len(arr) - 1\n"
                "    while left <= right:\n"
                "        mid = (left + right) // 2\n"
                "        if arr[mid] == target:\n"
                "            return mid\n"
                "        elif arr[mid] < target:\n"
                "            left = mid + 1\n"
                "        else:\n"
                "            right = mid - 1\n"
                "    return -1\n"
                "```"
            )
        elif "fibonacci" in q_lower:
            answer = (
                "Here is how to generate Fibonacci numbers in Python using dynamic programming / memoization:\n\n"
                "```python\n"
                "def fibonacci(n: int) -> list[int]:\n"
                "    if n <= 0:\n"
                "        return []\n"
                "    if n == 1:\n"
                "        return [0]\n"
                "    seq = [0, 1]\n"
                "    for _ in range(2, n):\n"
                "        seq.append(seq[-1] + seq[-2])\n"
                "    return seq\n\n"
                "# Example:\n"
                "print(fibonacci(8))  # Output: [0, 1, 1, 2, 3, 5, 8, 13]\n"
                "```"
            )
        elif "code" in q_lower or "python" in q_lower or "script" in q_lower or "program" in q_lower:
            answer = (
                f"Here is a Python implementation addressing your request:\n\n"
                "```python\n"
                "# COALINTEL Python Solution\n"
                "def execute_task():\n"
                "    print(\"Executing requested algorithm with high efficiency...\")\n"
                "    data = [i ** 2 for i in range(10)]\n"
                "    return {\"status\": \"SUCCESS\", \"computed\": data}\n\n"
                "if __name__ == '__main__':\n"
                "    output = execute_task()\n"
                "    print(f\"Result: {output}\")\n"
                "```\n\n"
                "*(For custom real-time GenAI code synthesis on arbitrary prompts, configure a valid LLM API key (`LLM_API_KEY` or `GEMINI_API_KEY`) in the environment.)*"
            )
        elif "what is python" in q_lower:
            answer = (
                "Python is a versatile, high-level programming language known for its clear syntax and readability. "
                "It is widely used in data science, artificial intelligence, backend development, and automation."
            )
        elif "recursion" in q_lower:
            answer = (
                "Recursion is a programming technique where a function calls itself to solve smaller subproblems "
                "of the original problem until reaching a base termination case."
            )
        elif "tcp/ip" in q_lower or "tcp ip" in q_lower:
            answer = (
                "TCP/IP (Transmission Control Protocol/Internet Protocol) is the foundational communications protocol suite "
                "that standardizes how data is packetized, addressed, transmitted, routed, and received across network connections."
            )
        elif "machine learning" in q_lower:
            answer = (
                "Machine Learning (ML) is a subset of artificial intelligence where algorithms learn patterns and relationships "
                "from historical data to make predictions or decisions without being explicitly rule-programmed."
            )

        # 3. Conceptual mining questions
        elif "what is coal" in q_lower or q_lower == "coal":
            answer = (
                "Coal is a combustible black or dark brownish sedimentary rock formed from ancient plant material subjected to "
                "heat and pressure over geological eras. It serves as a primary energy source for thermal power generation and steelmaking."
            )
        elif "overburden removal" in q_lower or "what is obr" in q_lower or "what is overburden" in q_lower:
            answer = (
                "Overburden removal (OBR) is the operational process in surface/open-cast mining where overlying rock, soil, and earth "
                "are excavated and removed to uncover the economically extractable coal seam below."
            )
        elif "open cast" in q_lower or "opencast" in q_lower:
            answer = (
                "Opencast (surface) mining is an extraction method used when mineral or coal deposits are located relatively close to the surface, "
                "excavating from the ground level downward."
            )
        else:
            answer = (
                f"COALINTEL AI Assistant: General conceptual response for \"{q_clean}\". "
                "This topic pertains to general knowledge and technical mining concepts. "
                "To enable real-time generative responses for general questions, configure a valid LLM API key (`LLM_API_KEY` or `GEMINI_API_KEY`) in the environment."
            )

        return {
            "answer": answer,
            "text": answer,
            "citations": [],
            "evidence_chunks": [],
            "provider": "degraded",
            "degraded_mode": True,
            "mode": "GENERAL_AI"
        }


class GeminiLLMProvider(BaseLLMProvider):
    """
    Hosted Gemini API LLM Provider implementation with direct REST API invocation and SDK fallback.
    """
    provider_name: str = "gemini"

    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash", timeout: float = 10.0):
        self.api_key = api_key
        self.model_name = model_name or "gemini-3.6-flash"
        self.timeout = timeout
        self.degraded_fallback = DegradedLLMProvider()

    @staticmethod
    def _sanitize_log_message(msg: str, secret_key: Optional[str] = None) -> str:
        """Sanitizes error text to ensure API keys, auth headers, and query parameters are never logged."""
        if not msg:
            return ""
        clean = re.sub(r"key=[A-Za-z0-9_\-]+", "key=[REDACTED]", msg)
        clean = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", clean)
        if secret_key and len(secret_key.strip()) >= 4:
            clean = clean.replace(secret_key.strip(), "[REDACTED]")
        return clean.strip()[:200]

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        if not self.api_key or self.api_key.strip() in ["", "your-api-key-here"]:
            return None

        # Try specified model and common active fallbacks
        candidate_models = [self.model_name]
        for fallback in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        for model in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
                else:
                    clean_resp = self._sanitize_log_message(resp.text[:200], self.api_key)
                    logger.warning(
                        f"provider=gemini model={model} HTTP failure status={resp.status_code} response='{clean_resp}'"
                    )
            except Exception as rest_err:
                clean_err = self._sanitize_log_message(str(rest_err), self.api_key)
                logger.warning(
                    f"provider=gemini model={model} request error ({type(rest_err).__name__}): {clean_err}"
                )

        # Try SDK fallback if available
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            if response and hasattr(response, "text") and response.text:
                return response.text
        except Exception as sdk_err:
            clean_sdk_err = self._sanitize_log_message(str(sdk_err), self.api_key)
            logger.warning(
                f"provider=gemini SDK fallback error ({type(sdk_err).__name__}): {clean_sdk_err}"
            )

        return None

    def generate(self, prompt: str) -> str:
        api_res = self._call_gemini_api(prompt)
        if api_res:
            return api_res
        return self.degraded_fallback.generate(prompt)

    def generate_general_ai(self, query: str) -> Dict[str, Any]:
        if not self.api_key or self.api_key.strip() in ["", "your-api-key-here"]:
            return self.degraded_fallback.generate_general_ai(query)

        sys_prompt = (
            "You are COALINTEL AI, an intelligent technical assistant for Coal India Limited (CIL) and CMPDI. "
            "Provide a direct, helpful, and technically accurate answer to the user's question.\n\n"
            f"User Question: {query}\n\n"
            "Answer:"
        )
        api_res = self._call_gemini_api(sys_prompt)
        if api_res:
            return {
                "answer": api_res.strip(),
                "citations": [],
                "evidence_chunks": [],
                "provider": "gemini",
                "degraded_mode": False,
                "mode": "GENERAL_AI"
            }

        fallback_res = self.degraded_fallback.generate_general_ai(query)
        fallback_res["provider"] = "degraded"
        return fallback_res

    def generate_completion(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        ans = self.generate(prompt)
        return {
            "answer": ans,
            "citations": [],
            "degraded_mode": not bool(self.api_key and self.api_key != "your-api-key-here"),
            "provider": "gemini"
        }


class OpenAILLMProvider(BaseLLMProvider):
    """
    Hosted OpenAI API LLM Provider implementation.
    """
    provider_name: str = "openai"

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", timeout: float = 10.0):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.degraded_fallback = DegradedLLMProvider()

    def generate(self, prompt: str) -> str:
        if not self.api_key or self.api_key == "your-api-key-here":
            return self.degraded_fallback.generate(prompt)
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout
            )
            return response.choices[0].message.content
        except Exception as err:
            logger.warning(f"OpenAI API invocation failed ({err}). Falling back to degraded grounded synthesis.")
            return self.degraded_fallback.generate(prompt)

    def generate_general_ai(self, query: str) -> Dict[str, Any]:
        if not self.api_key or self.api_key.strip() in ["", "your-api-key-here"]:
            return self.degraded_fallback.generate_general_ai(query)
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are COALINTEL AI Assistant for Coal India Limited."},
                    {"role": "user", "content": query}
                ],
                timeout=self.timeout
            )
            return {
                "answer": response.choices[0].message.content.strip(),
                "citations": [],
                "evidence_chunks": [],
                "provider": "openai",
                "degraded_mode": False,
                "mode": "GENERAL_AI"
            }
        except Exception as err:
            logger.warning(f"OpenAI General AI call failed ({err}).")
            return self.degraded_fallback.generate_general_ai(query)

    def generate_completion(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        ans = self.generate(prompt)
        return {
            "answer": ans,
            "citations": [],
            "degraded_mode": not bool(self.api_key and self.api_key != "your-api-key-here"),
            "provider": "openai"
        }


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    timeout: Optional[float] = None
) -> BaseLLMProvider:
    """
    Factory function returning the configured LLM provider according to environment settings.
    """
    p_name = (provider_name or settings.LLM_PROVIDER).lower()
    key = (
        api_key
        or settings.LLM_API_KEY
        or getattr(settings, "GEMINI_API_KEY", "")
        or getattr(settings, "GOOGLE_API_KEY", "")
        or os.getenv("GEMINI_API_KEY", "")
        or os.getenv("GOOGLE_API_KEY", "")
        or os.getenv("LLM_API_KEY", "")
    )
    m_name = model_name or settings.LLM_MODEL_NAME
    t_out = timeout or settings.LLM_TIMEOUT_SECONDS

    if p_name == "gemini":
        return GeminiLLMProvider(api_key=key, model_name=m_name, timeout=t_out)
    elif p_name == "openai":
        return OpenAILLMProvider(api_key=key, model_name=m_name, timeout=t_out)
    else:
        return DegradedLLMProvider()
