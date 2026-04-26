import re
from pathlib import Path
from typing import Dict, List

import yaml


TOKEN_PATTERN = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> set[str]:
    """Return lowercase word tokens for deterministic matching."""
    return set(TOKEN_PATTERN.findall(text.lower()))


def load_context_docs(path: str) -> List[Dict]:
    """Load context YAML files from a directory."""
    docs: List[Dict] = []
    for file_path in sorted(Path(path).glob("*.yaml")):
        with open(file_path, encoding="utf-8") as yaml_file:
            doc = yaml.safe_load(yaml_file) or {}
        docs.append(doc)
    return docs


def _keyword_items(keywords) -> list[tuple[str, float]]:
    if isinstance(keywords, dict):
        return [(str(keyword).lower(), float(weight)) for keyword, weight in keywords.items()]
    return [(str(keyword).lower(), 1.0) for keyword in keywords or []]


def _keyword_matches(keyword: str, request_tokens: set[str], request_text: str) -> bool:
    keyword_tokens = tokenize(keyword)
    if not keyword_tokens:
        return False
    if len(keyword_tokens) == 1:
        return next(iter(keyword_tokens)) in request_tokens
    return keyword in request_text


def retrieve_contexts(user_request: str, docs: List[Dict], k: int = 2) -> List[Dict]:
    """Retrieve top-k context docs by weighted keyword overlap."""
    request_text = user_request.lower()
    request_tokens = tokenize(user_request)
    scored_docs = []

    for index, doc in enumerate(docs):
        score = 0.0
        matched_keywords = []
        for keyword, weight in _keyword_items(doc.get("keywords")):
            if _keyword_matches(keyword, request_tokens, request_text):
                score += weight
                matched_keywords.append(keyword)
        enriched_doc = dict(doc)
        enriched_doc["retrieval_score"] = score
        enriched_doc["matched_keywords"] = matched_keywords
        scored_docs.append((score, index, enriched_doc))

    ranked = sorted(scored_docs, key=lambda item: (-item[0], item[1]))
    return [doc for _, _, doc in ranked[: max(k, 0)]]
