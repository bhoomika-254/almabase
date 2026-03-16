"""
Groq API integration for answer generation with citation-forcing prompts.
Generates 3 answer candidates per question (detailed, concise, executive strategies).
"""
import json
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"

RAW_QUESTIONNAIRE_SYSTEM_PROMPT = """You are a precise compliance questionnaire answering assistant.

Your task:
1. Read the raw questionnaire text — questions may span multiple lines and be formatted in any style.
2. Identify each distinct question and assign it a sequential number starting at 1.
3. Answer each question thoroughly using ONLY the provided reference documents.

STRICT RULES:
1. Answer ONLY using the provided reference documents. Do NOT use outside knowledge.
2. For every claim, cite the EXACT verbatim text from the source document — copy the words character-for-character. Do not paraphrase or summarise the quote.
3. Include as many citations as needed to fully support the answer — more citations means higher confidence.
4. If the answer to a question is NOT present anywhere in the reference documents, you MUST set not_found: true and set answer to exactly: "Not present in the document". Do NOT guess, do NOT elaborate, do NOT say anything else.
5. Keep answers professional, complete, and detailed.
6. confidence_score should reflect how thoroughly the reference documents cover the question: 0.9+ if fully covered, 0.7-0.9 if mostly covered, below 0.5 only if the information is scarce or absent.

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

CITATION_SYSTEM_PROMPT = """You are a precise compliance questionnaire answering assistant.

STRICT RULES:
1. Answer ONLY using the provided reference documents. Do NOT use outside knowledge.
2. For every claim, cite the EXACT verbatim text from the source document — copy the words character-for-character.
3. If the answer to a question is NOT present anywhere in the reference documents, you MUST set not_found: true and set answer to exactly: "Not present in the document". Do NOT guess, do NOT elaborate, do NOT say anything else.
4. Do NOT infer, extrapolate, or assume beyond what is explicitly written.
5. Keep answers professional, complete, and detailed.
6. Include as many citations as needed to fully support the answer.

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
    If a single long-text item is passed, treat it as a raw questionnaire document."""
    doc_sections = "\n\n".join(
        f"=== {name} ===\n{content}" for name, content in reference_docs.items()
    )

    # Raw questionnaire mode: one item whose text is the full document
    if len(questions) == 1 and len(questions[0]["text"]) > 200:
        return f"""Questionnaire Document:
{questions[0]["text"]}

Reference Documents:
{doc_sections}

Extract every distinct question from the questionnaire document above. Answer each question using ONLY the reference documents. For each answer include the exact question_text as it appears in the questionnaire. Respond with valid JSON containing an "answers" array."""

    # Normal mode: pre-parsed numbered questions
    questions_text = "\n".join(
        f"{q['number']}. {q['text']}" for q in questions
    )

    return f"""Questions:
{questions_text}

Reference Documents:
{doc_sections}

Answer ALL questions using ONLY the reference documents above. For each answer include the question_text exactly as given. Respond with valid JSON containing an "answers" array with one object per question."""


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
