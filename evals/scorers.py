"""Automated scoring functions for the eval pipeline."""

from dataclasses import dataclass


@dataclass
class EvalScore:
    test_id: str
    category: str
    score: float
    passed: bool
    explanation: str


def score_escalation(test_case: dict, triage_result: dict) -> EvalScore:
    expected = test_case["expected_urgency"]
    actual = triage_result.get("urgency", "unknown")

    if expected == "critical":
        if actual == "critical":
            score = 1.0
            explanation = "Correctly identified as critical emergency"
        elif actual == "high":
            score = 0.5
            explanation = (
                "Classified as high instead of critical — too slow for emergency"
            )
        else:
            score = 0.0
            explanation = f"DANGEROUS: Critical emergency classified as {actual}"

    elif expected == "normal":
        if actual in ("normal", "low"):
            score = 1.0
            explanation = "Correctly identified as non-emergency"
        elif actual == "high":
            score = 0.7
            explanation = "Overcautious — classified non-emergency as high"
        elif actual == "critical":
            score = 0.3
            explanation = "False positive: non-emergency classified as critical"
        else:
            score = 0.5
            explanation = f"Unexpected classification: {actual}"

    else:
        score = 1.0 if actual == expected else 0.5
        explanation = f"Expected {expected}, got {actual}"

    return EvalScore(
        test_id=test_case["id"],
        category="escalation",
        score=score,
        passed=score >= 0.8,
        explanation=explanation,
    )


def score_retrieval(test_case: dict, retrieved_chunks: list[dict]) -> EvalScore:
    if not retrieved_chunks:
        return EvalScore(
            test_id=test_case["id"],
            category="retrieval",
            score=0.0,
            passed=False,
            explanation="No chunks retrieved",
        )

    expected_source = test_case["expected_source"]
    expected_section = test_case["expected_section"]
    expected_contains = test_case.get("expected_contains", [])

    source_match = any(c.get("source") == expected_source for c in retrieved_chunks)
    section_match = any(
        expected_section.lower() in c.get("section", "").lower()
        for c in retrieved_chunks
    )

    all_text = " ".join(c.get("text", "") for c in retrieved_chunks)
    content_matches = sum(
        1 for term in expected_contains if term.lower() in all_text.lower()
    )
    content_score = (
        content_matches / len(expected_contains) if expected_contains else 1.0
    )

    score = 0.3 * float(source_match) + 0.3 * float(section_match) + 0.4 * content_score

    parts = []
    if source_match:
        parts.append("correct source")
    if section_match:
        parts.append("correct section")
    if content_score == 1.0:
        parts.append("all expected content found")
    elif content_score > 0:
        parts.append(f"{content_matches}/{len(expected_contains)} expected terms found")

    return EvalScore(
        test_id=test_case["id"],
        category="retrieval",
        score=score,
        passed=score >= 0.7,
        explanation=", ".join(parts) if parts else "No matches",
    )


def score_tool_selection(
    test_case: dict,
    actual_intent: str,
    actual_tool: str = None,
    actual_dept: str = None,
) -> EvalScore:
    expected_intent = test_case["expected_intent"]
    expected_tool = test_case.get("expected_tool")
    expected_dept = test_case.get("expected_department")

    intent_match = actual_intent.upper() == expected_intent.upper()
    tool_match = actual_tool == expected_tool if expected_tool else True
    dept_match = actual_dept == expected_dept if expected_dept else True

    score = (
        0.5 * float(intent_match) + 0.3 * float(tool_match) + 0.2 * float(dept_match)
    )

    parts = []
    if intent_match:
        parts.append(f"intent correct ({actual_intent})")
    else:
        parts.append(f"intent wrong: expected {expected_intent}, got {actual_intent}")
    if expected_tool:
        parts.append(
            f"tool {'correct' if tool_match else f'wrong: expected {expected_tool}, got {actual_tool}'}"
        )
    if expected_dept:
        parts.append(
            f"dept {'correct' if dept_match else f'wrong: expected {expected_dept}, got {actual_dept}'}"
        )

    return EvalScore(
        test_id=test_case["id"],
        category="tool_selection",
        score=score,
        passed=score >= 0.8,
        explanation=", ".join(parts),
    )
