"""
Misconception Catalogue

Each misconception has:
- id: unique identifier
- label: human-readable name
- description: plain-language, non-judgmental description
- step: the mathematical step involved
- why_it_matters: one sentence linking to later topics
"""

MISCONCEPTIONS = {
    "DIST_PARTIAL": {
        "id": "DIST_PARTIAL",
        "label": "Partial Distribution",
        "description": "The multiplier was applied to only the first term inside the brackets.",
        "step": "Distributive property: a(b + c) = ab + ac — the multiplier must reach every term.",
        "why_it_matters": "Partial distribution leads to errors in expanding expressions, factoring, and solving equations with brackets.",
    },
    "DIST_NEG_SIGN": {
        "id": "DIST_NEG_SIGN",
        "label": "Negative Sign Distribution",
        "description": "A negative multiplier was not correctly applied to both terms, especially negative × negative.",
        "step": "Distributive property with negatives: −a(b − c) = −ab + ac.",
        "why_it_matters": "Sign errors propagate through multi-step equations and inequality solving.",
    },
    "LIKE_UNLIKE": {
        "id": "LIKE_UNLIKE",
        "label": "Combining Unlike Terms",
        "description": "Terms with different variables or a variable and a constant were combined.",
        "step": "Like terms have identical variable parts (e.g., 3x and 5x); constants combine with constants.",
        "why_it_matters": "Combining unlike terms breaks simplification and makes later equation solving unreliable.",
    },
    "LIKE_NEG_COEFF": {
        "id": "LIKE_NEG_COEFF",
        "label": "Negative Coefficient Sign Errors",
        "description": "Sign errors when combining negative coefficients.",
        "step": "Adding negative coefficients: −2x + (−3x) = −5x.",
        "why_it_matters": "Sign fluency is essential for inverse operations and equation solving.",
    },
    "SUBST_ORDER": {
        "id": "SUBST_ORDER",
        "label": "Substitution Without Multiplication",
        "description": "A value was substituted for a variable but the coefficient was not multiplied.",
        "step": "Substitution: replace the variable, then follow order of operations (multiply before add).",
        "why_it_matters": "This error appears in evaluating functions, formulas, and checking solutions.",
    },
    "INV_WRONG_OP": {
        "id": "INV_WRONG_OP",
        "label": "Wrong Inverse Operation",
        "description": "The inverse operation was not correctly chosen (e.g., adding instead of subtracting to undo addition).",
        "step": "Inverse operations: to undo +a, subtract a; to undo ×a, divide by a (a ≠ 0).",
        "why_it_matters": "Choosing the wrong inverse prevents isolating the variable and solving equations.",
    },
    "INV_ORDER": {
        "id": "INV_ORDER",
        "label": "Inverse Operations in Wrong Order",
        "description": "Inverse operations were applied in the wrong sequence or stopped before the variable was isolated.",
        "step": "Reverse order of operations: undo addition/subtraction first, then multiplication/division.",
        "why_it_matters": "Order matters — applying operations out of sequence gives an incorrect result.",
    },
    "INV_ONE_SIDE": {
        "id": "INV_ONE_SIDE",
        "label": "Operation Applied to One Side Only",
        "description": "An operation was applied to only one side of the equation.",
        "step": "Balance principle: whatever you do to one side, you must do to the other.",
        "why_it_matters": "This breaks the equality and leads to incorrect solutions.",
    },
    "INV_NEG_DIV": {
        "id": "INV_NEG_DIV",
        "label": "Sign Lost Dividing by Negative",
        "description": "The negative sign was lost when dividing both sides by a negative coefficient.",
        "step": "Dividing by a negative: −2x = 6 → x = −3 (sign flips).",
        "why_it_matters": "Sign errors with negative coefficients are a major source of mistakes in algebra.",
    },
    "INT_COMPARE_ABS": {
        "id": "INT_COMPARE_ABS",
        "label": "Comparing Absolute Values",
        "description": "Numbers were compared by absolute size rather than position on the number line.",
        "step": "On the number line, negative numbers are left of positive numbers; more negative means smaller.",
        "why_it_matters": "Understanding order is foundational for inequalities and coordinate geometry.",
    },
    "ORDER_OPS": {
        "id": "ORDER_OPS",
        "label": "Order of Operations",
        "description": "Operations were performed left-to-right instead of following precedence rules.",
        "step": "PEMDAS/BODMAS: brackets, exponents, multiplication/division (left-to-right), addition/subtraction (left-to-right).",
        "why_it_matters": "Order of operations applies to every algebraic expression and equation.",
    },
    "INEQ_FLIP": {
        "id": "INEQ_FLIP",
        "label": "Inequality Sign Flip",
        "description": "The inequality direction was not reversed when multiplying or dividing by a negative number.",
        "step": "Multiplying/dividing an inequality by a negative flips the sign: −2x > 6 → x < −3.",
        "why_it_matters": "This rule is critical for solving inequalities correctly.",
    },
    "ARITHMETIC_SLIP": {
        "id": "ARITHMETIC_SLIP",
        "label": "Arithmetic Slip",
        "description": "A calculation error (addition, subtraction, multiplication, or division) unrelated to the algebraic concept.",
        "step": "Basic arithmetic facts and procedures.",
        "why_it_matters": "Arithmetic fluency supports algebraic work but is a separate skill.",
    },
    "UNCLEAR": {
        "id": "UNCLEAR",
        "label": "Unclear Pattern",
        "description": "The answer does not match a known misconception pattern; more evidence is needed.",
        "step": "Not applicable — the response pattern is not diagnostic.",
        "why_it_matters": "Some errors don't reveal a systematic misunderstanding; they may be slips or guesses.",
    },
}


def get_misconception(misconception_id: str) -> dict:
    return MISCONCEPTIONS.get(misconception_id, MISCONCEPTIONS["UNCLEAR"])


def get_all_misconceptions() -> list[dict]:
    return list(MISCONCEPTIONS.values())


# Evidence combination parameters (documented in ENGINE.md)
EVIDENCE_PARAMS = {
    "diagnostic_match": 2,           # +2 to hypothesis (was +1, doubled for half-point storage)
    "followup_consistent": 4,        # +2 * 2
    "followup_contradicts": -3,      # -1.5 * 2
    "unsure": 0,
    "practice_error": 1,             # +0.5 * 2
    "retest_error": 1,               # +0.5 * 2
    "insufficient_threshold": 4,     # score < 4 (i.e., < 2.0)
    "possible_threshold": 6,         # score < 6 (i.e., < 3.0)
    "supported_threshold": 6,        # score >= 6 (i.e., >= 3.0)
    "margin_required": 3,            # margin >= 1.5 over runner-up (stored as 3)
    "requires_followup_for_supported": True,
}


def hypothesis_status(score: int, runner_up_score: int, has_followup_evidence: bool) -> str:
    """
    Determine hypothesis status from evidence score.
    Scores are stored doubled (half-points as integers).
    """
    params = EVIDENCE_PARAMS

    if score < params["insufficient_threshold"]:
        return "insufficient"
    if score < params["possible_threshold"]:
        return "possible"
    # For "supported", need threshold, margin, and at least one follow-up
    if score >= params["supported_threshold"]:
        margin = score - runner_up_score
        if margin >= params["margin_required"] and has_followup_evidence:
            return "supported"
    return "possible"


def confidence_wording(status: str) -> str:
    """Return the honest, non-judgmental wording for a hypothesis status."""
    return {
        "insufficient": "We don't have enough evidence yet to say why.",
        "possible": "One possible explanation, still checking.",
        "supported": "The evidence supports this explanation.",
    }.get(status, "We don't have enough evidence yet to say why.")