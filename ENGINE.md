# Diagnostic Engine Specification

This document describes the rules, thresholds, and algorithms powering the MisconceptionMap diagnostic engine. The engine is a pure Python module (`backend/app/engine/`) with no web or database dependencies.

## State Machine

The learning journey follows this exact flow:

```
START → DIAGNOSTIC (check & record response)
  → known answer pattern?
      yes ("potential misconception") → TARGETED_FOLLOWUP
      no  ("correct or unclear")      → CHECK_UNDERSTANDING (transfer question / more evidence)
  → COMBINE_EVIDENCE
  → evidence sufficient?
      yes → EXPLAIN_SUPPORTED_HYPOTHESIS
      no  → REPORT_UNCERTAINTY
  → TARGETED_PRACTICE (3 questions, feedback after each)
  → FRESH_RETEST (3 new questions)
  → UPDATE_PROGRESS_RECORD
  → RESULTS + MISCONCEPTION MAP
```

### Phases

| Phase | Purpose | Questions | Advances When |
|-------|---------|-----------|---------------|
| `diagnostic` | Initial assessment | 3-4 per level | All diagnostic questions answered |
| `followup` | Discriminate between hypotheses | 1-2 per hypothesis | Follow-up questions answered |
| `check_understanding` | Transfer check (all-correct diagnostic) | 2 per level | Check questions answered |
| `practice` | Targeted practice | 3 questions | 3 practice questions answered |
| `retest` | Fresh assessment | 3 new questions | 3 retest questions answered |
| `results` | Show explanation & evidence trail | — | Automatic |
| `completed` | Journey finished | — | After results viewed |

## Evidence Combination Model

Each learner × skill × misconception has an **evidence score** (stored as integer = half-points × 2).

### Score Updates

| Event | Score Delta | Notes |
|-------|-------------|-------|
| Diagnostic distractor matching H | +2 (+1.0) | Only for the matched hypothesis |
| Follow-up consistent with H | +4 (+2.0) | Sets `has_followup=true` |
| Follow-up contradicts H (correct answer) | -3 (-1.5) | For each discriminated hypothesis |
| "I'm not sure" | 0 | Neutral, marks item "unclear" |
| Practice error tagged to H | +1 (+0.5) | Informational |
| Retest error tagged to H | +1 (+0.5) | Informational |

### Status Thresholds

| Status | Score | Margin | Follow-up Required |
|--------|-------|--------|-------------------|
| Insufficient | < 4 (< 2.0) | — | — |
| Possible | 4–5 (2.0–2.5) | — | — |
| Supported | ≥ 6 (≥ 3.0) | ≥ 3 (≥ 1.5) over runner-up | Yes |

**Status wording (shown to learner):**
- Insufficient: "We don't have enough evidence yet to say why."
- Possible: "One possible explanation, still checking."
- Supported: "The evidence supports this explanation."

### Single-Slip Rule

One isolated error with no pattern → labelled "possible slip" (ARITHMETIC_SLIP), not a misconception.

## Discriminating Follow-Ups

Follow-up questions are **chosen per hypothesis** to separate competing explanations. They are not generic.

Example for `DIST_PARTIAL` (partial distribution):
- Diagnostic: Student answers `3x + 2 = 15` for `3(x + 2) = 15`
- Follow-up: "If x = 4, which equals 3(x + 2)?" → `3x + 6` (18) vs `3x + 2` (14)
- If student answers follow-up **correctly** → evidence for DIST_PARTIAL **decreases** (-1.5)
- If student answers follow-up **incorrectly** with DIST_PARTIAL distractor → evidence **increases** (+2.0)

This is the key discriminating mechanism: a follow-up can **lower** a hypothesis score.

## Question Selection Rules

### Diagnostic
- Fixed set per level (3-4 questions)
- Every wrong option maps to exactly one misconception ID (or ARITHMETIC_SLIP/UNCLEAR)
- Includes "I'm not sure yet" option (neutral)

### Follow-Up
- Selected based on top hypothesis after diagnostic
- Must have `discriminates` field listing target misconceptions
- At least 2 follow-ups per misconception in content

### Check Understanding
- Used when diagnostic is all-correct
- Transfer questions in different form (word problems, area models, etc.)
- 2 per level minimum

### Practice
- 3 questions per session
- Target the supported/possible hypothesis
- If insufficient evidence → general skill practice pool
- **Different forms**: standard, reversed, negative multiplier, word/area model
- Never repeats a question seen in diagnostic/follow-up/check

### Retest
- 3 **new** questions (disjoint from diagnostic/follow-up/practice/check pools)
- Same skill, different surface forms
- Pool ≥ 6 items per level to ensure freshness
- If pool exhausted for learner → reuse oldest, label "partially repeated"
- Randomized option order per attempt (server-side)

## Progress & Mastery Vocabulary

**Never use "mastered".** Use:

| Status | Meaning | Trigger |
|--------|---------|---------|
| `not_assessed` | No data yet | Initial state |
| `evidence_of_difficulty` | Diagnostic suggests issue | Any misconception score > 0 |
| `practicing` | In practice phase | Practice started |
| `encouraging_evidence` | Retest ≥ 2/3 correct | First retest passes |
| `consistent_evidence` | Second retest passes | Retest count ≥ 2, both ≥ 2/3 |
| `needs_more_practice` | Retest < 2/3 | Retest fails |

## Evidence Trail (UI)

Every hypothesis shown in Insights includes an evidence trail:

```
Question → Your answer → What that pattern suggests
```

Example:
> "Rewrite 3(x+2)=15 without brackets" → "3x+2=15" → "Consistent with Partial Distribution: multiplier applied only to first term"

## Implementation Notes

- Engine class: `DiagnosticEngine` in `backend/app/engine/state_machine.py`
- Content loaded via `ContentLoader` from YAML files
- Misconception definitions in `backend/app/engine/misconceptions.py`
- All thresholds in `EVIDENCE_PARAMS` dictionary (configurable)
- Unit tests in `backend/tests/test_engine.py`

## Adding New Misconceptions

1. Add to `MISCONCEPTIONS` dict in `misconceptions.py`
2. Add evidence parameters if different from defaults
3. Create content items with the new `misconception_id`
4. Add discriminating follow-ups
5. Run content verification tests