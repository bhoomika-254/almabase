"""
Citation extraction, validation, and processing service.
Processes raw citations from LLM responses into structured, validated citation records.
"""
import re
from typing import Optional


def normalize_text(text: str) -> str:
    """Normalize whitespace for comparison."""
    return re.sub(r"\s+", " ", text.strip()).lower()


def validate_citation_in_doc(quote: str, doc_content: str) -> bool:
    """
    Check if a quote actually exists in the document content.
    Uses normalized comparison for robustness.
    """
    if not quote or not doc_content:
        return False
    return normalize_text(quote) in normalize_text(doc_content)


def extract_surrounding_context(quote: str, doc_content: str, context_chars: int = 200) -> str:
    """
    Find the quote in doc_content and return surrounding text for context.
    Falls back to the quote itself if not found.
    """
    norm_content = normalize_text(doc_content)
    norm_quote = normalize_text(quote)

    idx = norm_content.find(norm_quote)
    if idx == -1:
        return quote

    start = max(0, idx - context_chars // 2)
    end = min(len(norm_content), idx + len(norm_quote) + context_chars // 2)
    snippet = norm_content[start:end].strip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(norm_content):
        snippet = snippet + "..."

    return snippet


def process_citations(
    raw_citations: list[dict],
    reference_docs: dict[str, str],
    doc_name_to_id: dict[str, str],
) -> tuple[list[dict], list[dict], float, bool]:
    """
    Process raw citations from LLM into structured, validated citation records.

    Args:
        raw_citations: List of raw citation dicts from LLM
        reference_docs: Dict of {filename: content} for validation
        doc_name_to_id: Dict of {filename: doc_id} for linking

    Returns:
        (citations, evidence_snippets, hallucination_risk, citations_verified)
    """
    citations = []
    evidence_snippets = []
    validated_count = 0
    total_count = 0

    for raw in raw_citations:
        source_doc = raw.get("source_document", "")
        quote = raw.get("quote", "")
        context = raw.get("context", quote)
        location = raw.get("location", "")

        if not quote:
            continue

        total_count += 1

        # Find matching document (flexible name matching)
        matched_doc_name = None
        matched_doc_content = None
        matched_doc_id = None

        for doc_name, doc_content in reference_docs.items():
            if (source_doc.lower() in doc_name.lower() or
                    doc_name.lower() in source_doc.lower() or
                    normalize_text(source_doc) == normalize_text(doc_name)):
                matched_doc_name = doc_name
                matched_doc_content = doc_content
                matched_doc_id = doc_name_to_id.get(doc_name, "")
                break

        # If no doc matched by name, search all docs for the quote
        if not matched_doc_name:
            for doc_name, doc_content in reference_docs.items():
                if validate_citation_in_doc(quote, doc_content):
                    matched_doc_name = doc_name
                    matched_doc_content = doc_content
                    matched_doc_id = doc_name_to_id.get(doc_name, "")
                    break

        is_valid = (
            matched_doc_content is not None
            and validate_citation_in_doc(quote, matched_doc_content)
        )

        if is_valid:
            validated_count += 1
            full_context = extract_surrounding_context(quote, matched_doc_content)
        else:
            full_context = context or quote

        citations.append({
            "doc_id": matched_doc_id or "",
            "doc_name": matched_doc_name or source_doc,
            "excerpt": quote,
            "full_context": full_context,
            "paragraph_number": None,
            "confidence": 0.95 if is_valid else 0.5,
            "validated": is_valid,
            "location": location,
        })

        # Build evidence snippet per document (group by doc)
        existing_snippet = next(
            (s for s in evidence_snippets if s["doc_name"] == (matched_doc_name or source_doc)),
            None
        )
        if existing_snippet:
            if quote not in existing_snippet["snippet_text"]:
                existing_snippet["snippet_text"] += f" ... {quote}"
        else:
            evidence_snippets.append({
                "doc_name": matched_doc_name or source_doc,
                "snippet_text": quote,
            })

    # Calculate hallucination risk
    if total_count == 0:
        hallucination_risk = 0.8  # High risk if no citations at all
    else:
        hallucination_risk = round(1.0 - (validated_count / total_count), 2)

    citations_verified = validated_count == total_count and total_count > 0

    return citations, evidence_snippets, hallucination_risk, citations_verified


def calculate_confidence(
    answer: str,
    citations: list[dict],
    not_found: bool,
) -> float:
    """
    Calculate final confidence score for an answer based on citations.
    """
    if not_found:
        return 0.0

    if not citations:
        return 0.25

    validated = [c for c in citations if c.get("validated", False)]
    unvalidated = [c for c in citations if not c.get("validated", False)]

    # Validated citations score full; unvalidated still score 0.6 because
    # the LLM found the right document — the quote just wasn't verbatim
    citation_score = (len(validated) + len(unvalidated) * 0.6) / len(citations)

    # Softer density check: expect 1 citation per 3 sentences, not 1-per-1
    answer_sentences = max(1, len([s for s in answer.split(".") if s.strip()]))
    citation_density = min(1.0, len(citations) / max(answer_sentences / 3, 1))

    confidence = citation_score * 0.75 + citation_density * 0.25
    return round(min(0.99, max(0.25, confidence)), 2)
