"""
Groq API integration for answer generation with citation-forcing prompts.
Generates 3 answer candidates per question (detailed, concise, executive strategies).
"""
import json
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"

RAW_QUESTIONNAIRE_SYSTEM_PROMPT = """You are a STRICT compliance questionnaire answering assistant. NEVER hallucinate or invent information.

Your task:
1. Read the raw questionnaire text and identify questions carefully.
2. For EACH question, search reference documents thoroughly.
3. Answer ONLY if information is explicitly present in the reference documents.

CRITICAL ANTI-HALLUCINATION RULES:
1. ONLY answer from provided reference documents. DO NOT use outside knowledge.
2. EVERY single claim MUST be backed by EXACT verbatim quote from the documents.
3. If a claim cannot be found EXACTLY in the documents, DO NOT include it.
4. If you cannot find ANY answer, immediately return not_found: true with answer: "Not found in the provided documents".
5. NEVER make up, infer, assume, or guess information.
6. NEVER split ONE question into multiple questions. Treat as single question.
7. For multi-part questions with 'and' or 'or': answer comprehensively as ONE question.
8. Include multiple citations for each claim — more citations = higher confidence.
9. confidence_score: 1.0 if fully answered with multiple citations, 0.7-0.9 if mostly covered, 0.3-0.6 if scarce, 0.0 if not_found.

VALIDATION: Before responding, verify EVERY citation exists verbatim in documents. If not found, mark not_found: true.

Respond with ONLY valid JSON (no markdown, no ```json blocks), in this exact format:
{
  "answers": [
    {
      "question_number": 1,
      "question_text": "Full question text exactly as found in the questionnaire",
      "answer": "Your detailed answer here",
      "confidence_score": 0.95,
      "not_found": false,
      "citations": [
        {
          "source_document": "DocumentName.pdf",
          "quote": "exact verbatim text copied from the document",
          "context": "the surrounding sentence or paragraph",
          "location": "section name or description"
        }
      ]
    }
  ]
}"""

CITATION_SYSTEM_PROMPT = """You are a STRICT compliance questionnaire answering assistant. ZERO tolerance for hallucination.

ANTI-HALLUCINATION MANDATE:
- ONLY answer using provided reference documents. NEVER use outside knowledge.
- EVERY claim MUST have EXACT verbatim text quote from the documents.
- If information is NOT in the documents, return not_found: true IMMEDIATELY.
- Do NOT infer, extrapolate, paraphrase, or assume anything beyond what is explicitly written.

ANSWER REQUIREMENTS:
- Answer is ONLY valid if it has AT LEAST ONE verified citation.
- Answers with NO citations must be marked not_found: true.
- Copy quotes character-for-character. Use triple-check before submitting.
- If unsure about a quote, DO NOT include it and mark not_found: true instead.

CONFIDENCE SCORING:
- 1.0 = Fully answered with multiple verified citations
- 0.8-0.9 = Mostly answered with 2+ citations
- 0.6-0.7 = Partially answered with at least 1 citation
- 0.3-0.5 = Minimal information with weak citations
- 0.0 = not_found = true (no information in documents)

Respond with ONLY valid JSON (no markdown, no ```json blocks), in this exact format:
{
  "answers": [
    {
      "question_number": 1,
      "question_text": "The exact question as written in the questionnaire",
      "answer": "Your answer text here",
      "confidence_score": 0.95,
      "not_found": false,
      "citations": [
        {
          "source_document": "DocumentName.pdf",
          "quote": "exact verbatim text copied from the document",
          "context": "the surrounding sentence or paragraph",
          "location": "section name or description"
        }
      ]
    }
  ]
}"""


def _build_user_prompt(question: str, reference_docs: dict[str, str], strategy: str) -> str:
    """Build the user prompt for a single question with specific strategy."""
    strategy_instructions = {
        "detailed": "Provide a thorough, complete answer covering all relevant details from the references.",
        "concise": "Provide a brief, direct answer using only the most critical information.",
        "executive": "Provide a high-level executive summary suitable for senior decision-makers.",
    }

    doc_sections = "\n\n".join(
        f"=== {name} ===\n{content}" for name, content in reference_docs.items()
    )

    return f"""Question: {question}

Strategy: {strategy_instructions.get(strategy, strategy_instructions['detailed'])}

Reference Documents:
{doc_sections}

Answer the question using ONLY the reference documents above. Respond with valid JSON only."""


def _build_batch_prompt(questions: list[dict], reference_docs: dict[str, str], strategy: str) -> str:
    """Build the user prompt for multiple questions at once.
    
    Two modes:
    - Raw mode (len(questions) == 1): Pass raw text to LLM, let it parse and split questions
    - Normal mode (len(questions) > 1): Pre-parsed questions (e.g., from CSV), answer each one
    
    The LLM will intelligently handle parsing regardless of formatting:
    - Questions separated by blank lines, newlines, or no separators
    - Single question spanning multiple lines vs multiple questions
    """
    doc_sections = "\n\n".join(
        f"=== {name} ===\n{content}" for name, content in reference_docs.items()
    )

    # Raw questionnaire mode: Single item, let LLM parse and extract questions
    if len(questions) == 1:
        question_text = questions[0]["text"]
        print(f"[PROMPT] Raw questionnaire mode: passing {len(question_text)} chars to LLM for parsing")
        return f"""Questionnaire Document:
{question_text}

Reference Documents:
{doc_sections}

Your task:
1. Identify and extract ALL distinct questions from the questionnaire document above
2. For each question, answer using ONLY the reference documents
3. Assign each question a sequential number starting at 1
4. If you cannot find an answer for a question, set not_found: true

Important:
- Do NOT split or fabricate questions
- If a question spans multiple lines and is NOT separated by blank lines, treat as ONE question
- Answer each question comprehensively with citations
- Respond with valid JSON containing an "answers" array"""

    # Normal mode: Pre-parsed numbered questions (e.g., from CSV)
    print(f"[PROMPT] Normal mode: {len(questions)} pre-parsed question(s)")
    questions_text = "\n".join(
        f"{q['number']}. {q['text']}" for q in questions
    )

    return f"""Questions:
{questions_text}

Reference Documents:
{doc_sections}

Answer ALL questions using ONLY the reference documents above. For each answer include the question_text exactly as given.
- If answer is NOT found in documents, set not_found: true and answer: "Not found in the provided documents"
- Every answer must have at least one citation or be marked not_found: true
Respond with valid JSON containing an "answers" array with one object per question."""


def generate_single_answer(
    question: str,
    reference_docs: dict[str, str],
    strategy: str = "detailed",
) -> dict:
    """
    Generate one answer candidate using Groq.
    Returns parsed JSON dict with answer, confidence_score, not_found, citations.
    """
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        prompt = _build_user_prompt(question, reference_docs, strategy)

        print(f"  [LLM] Calling Groq ({GROQ_MODEL}) strategy={strategy}...")
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": CITATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        print(f"  [LLM] Groq responded OK")

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  [LLM] JSON parse error: {e}")
        return {
            "answer": "Not present in the document",
            "confidence_score": 0.0,
            "not_found": True,
            "citations": [],
        }
    except Exception as e:
        print(f"  [LLM] ERROR: {type(e).__name__}: {e}")
        return {
            "answer": f"Error generating answer: {str(e)}",
            "confidence_score": 0.0,
            "not_found": True,
            "citations": [],
        }


def generate_answer_candidates(
    question: str,
    reference_docs: dict[str, str],
) -> list[dict]:
    """
    Generate 3 answer candidates for a question using different strategies — in parallel.
    Returns list of dicts: [{strategy, answer, confidence_score, not_found, citations}]
    """
    from concurrent.futures import ThreadPoolExecutor

    strategies = ["detailed", "concise", "executive"]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(generate_single_answer, question, reference_docs, strategy): (i, strategy)
            for i, strategy in enumerate(strategies)
        }
        results = {}
        for future in futures:
            i, strategy = futures[future]
            results[i] = future.result()

    return [
        {
            "candidate_id": i + 1,
            "generation_strategy": strategies[i],
            "answer": results[i].get("answer", "Not present in the document"),
            "confidence_score": results[i].get("confidence_score", 0.0),
            "not_found": results[i].get("not_found", False),
            "raw_citations": results[i].get("citations", []),
        }
        for i in range(len(strategies))
    ]


def generate_batch_answers(
    questions: list[dict],
    reference_docs: dict[str, str],
    strategy: str = "detailed",
) -> dict:
    """
    Generate answers for ALL questions in a single LLM call.
    Returns dict with answers array: {"answers": [{"question_number": 1, "answer": "...", ...}, ...]}
    """
    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        prompt = _build_batch_prompt(questions, reference_docs, strategy)

        is_raw_mode = len(questions) == 1 and len(questions[0]["text"]) > 200
        system_prompt = RAW_QUESTIONNAIRE_SYSTEM_PROMPT if is_raw_mode else CITATION_SYSTEM_PROMPT

        print(f"  [LLM] Calling Groq {'RAW' if is_raw_mode else 'BATCH'} mode ({GROQ_MODEL}), {len(questions)} input item(s)...")
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=8000,
        )
        print(f"  [LLM] Groq responded OK")

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        return parsed

    except json.JSONDecodeError as e:
        print(f"  [LLM] JSON parse error in batch mode: {e}")
        # Return fallback with "not found" for all questions
        return {
            "answers": [
                {
                    "question_number": q["number"],
                    "answer": "Not present in the document",
                    "confidence_score": 0.0,
                    "not_found": True,
                    "citations": [],
                }
                for q in questions
            ]
        }
    except Exception as e:
        print(f"  [LLM] ERROR in batch mode: {type(e).__name__}: {e}")
        return {
            "answers": [
                {
                    "question_number": q["number"],
                    "answer": f"Error generating answer: {str(e)}",
                    "confidence_score": 0.0,
                    "not_found": True,
                    "citations": [],
                }
                for q in questions
            ]
        }


def generate_batch_answer_candidates(
    questions: list[dict],
    reference_docs: dict[str, str],
) -> dict[int, list[dict]]:
    """
    Generate 1 answer per question using the detailed strategy.
    Makes 1 LLM call total for all questions.

    Returns dict mapping question_number -> list with 1 candidate:
    {
        1: [{candidate_id: 1, strategy: "detailed", question_text: "...", answer: "...", ...}],
        ...
    }
    """
    print(f"  [LLM] Generating answers for all questions in 1 batch call...")
    batch_result = generate_batch_answers(questions, reference_docs, "detailed")

    # Organize by question number
    question_candidates = {}
    for ans in batch_result.get("answers", []):
        q_num = ans.get("question_number")
        if q_num is None:
            continue

        question_candidates[q_num] = [{
            "candidate_id": 1,
            "generation_strategy": "detailed",
            "question_text": ans.get("question_text", ""),
            "answer": ans.get("answer", "Not present in the document"),
            "confidence_score": ans.get("confidence_score", 0.0),
            "not_found": ans.get("not_found", True),
            "raw_citations": ans.get("citations", []),
        }]

    # Fallback for any pre-parsed questions the LLM missed
    for q in questions:
        if q["number"] not in question_candidates and len(questions) > 1:
            question_candidates[q["number"]] = [{
                "candidate_id": 1,
                "generation_strategy": "detailed",
                "question_text": q["text"],
                "answer": "Not present in the document",
                "confidence_score": 0.0,
                "not_found": True,
                "raw_citations": [],
            }]

    return question_candidates


def generate_answers_from_raw(
    questionnaire_text: str,
    reference_docs: dict[str, str],
) -> dict:
    """
    Send raw questionnaire text to the LLM. The LLM identifies each question,
    numbers them, and answers them using the reference documents.

    Returns {"answers": [{question_number, question_text, answer, confidence_score, not_found, citations}]}
    """
    doc_sections = "\n\n".join(
        f"=== {name} ===\n{content}" for name, content in reference_docs.items()
    )
    prompt = f"""Questionnaire:
{questionnaire_text}

Reference Documents:
{doc_sections}

Identify each question in the questionnaire above, number them sequentially starting at 1, and answer each one using ONLY the reference documents. Respond with valid JSON only."""

    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)

        print(f"  [LLM] Calling Groq RAW QUESTIONNAIRE mode ({GROQ_MODEL})...")
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": RAW_QUESTIONNAIRE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=8000,
        )
        print(f"  [LLM] Groq responded OK")

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  [LLM] JSON parse error in raw mode: {e}")
        return {"answers": []}
    except Exception as e:
        print(f"  [LLM] ERROR in raw mode: {type(e).__name__}: {e}")
        return {"answers": []}
