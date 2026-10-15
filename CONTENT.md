# Content Specification & Authoring Guide

This document describes the misconception catalogue, content structure, and authoring process for MisconceptionMap.

## Misconception Catalogue

Each misconception has a unique ID, label, description, mathematical step, and why-it-matters statement.

### Current Catalogue (14 misconceptions)

| ID | Label | Description | Step | Why It Matters |
|----|-------|-------------|------|----------------|
| `DIST_PARTIAL` | Partial Distribution | Multiplier applied to only first term | a(b+c) = ab+ac — multiplier must reach every term | Errors in expanding, factoring, solving equations with brackets |
| `DIST_NEG_SIGN` | Negative Sign Distribution | Negative multiplier not correctly applied to both terms | −a(b−c) = −ab+ac | Sign errors propagate through multi-step equations |
| `LIKE_UNLIKE` | Combining Unlike Terms | Different variables or variable+constant combined | Like terms have identical variable parts | Breaks simplification and equation solving |
| `LIKE_NEG_COEFF` | Negative Coefficient Sign Errors | Sign errors combining negative coefficients | −2x + (−3x) = −5x | Sign fluency essential for inverse operations |
| `SUBST_ORDER` | Substitution Without Multiplication | Value substituted but coefficient not multiplied | Replace variable, then multiply before add | Appears in evaluating functions, formulas, checking solutions |
| `INV_WRONG_OP` | Wrong Inverse Operation | Inverse operation not correctly chosen | Undo +a → subtract a; undo ×a → divide by a | Prevents isolating variable |
| `INV_ORDER` | Inverse Operations Wrong Order | Operations applied in wrong sequence | Reverse order: undo +/− first, then ×/÷ | Order matters for correct result |
| `INV_ONE_SIDE` | Operation Applied to One Side Only | Operation on only one side of equation | Balance principle: do same to both sides | Breaks equality |
| `INV_NEG_DIV` | Sign Lost Dividing by Negative | Negative sign lost when dividing by negative | −2x = 6 → x = −3 | Major source of mistakes in algebra |
| `INT_COMPARE_ABS` | Comparing Absolute Values | Compared by absolute size not position | Negative numbers left of positive on number line | Foundational for inequalities |
| `ORDER_OPS` | Order of Operations | Left-to-right instead of precedence | PEMDAS/BODMAS | Applies to every algebraic expression |
| `INEQ_FLIP` | Inequality Sign Flip | Didn't flip sign when dividing by negative | −2x > 6 → x < −3 | Critical for solving inequalities |
| `ARITHMETIC_SLIP` | Arithmetic Slip | Calculation error unrelated to concept | Basic arithmetic facts | Separate skill from algebraic reasoning |
| `UNCLEAR` | Unclear Pattern | Answer doesn't match known pattern | Not diagnostic | May be slips or guesses |

## Content Structure

Items live in `backend/app/content/level{1-5}.yaml`.

### Item Schema

```yaml
- item_id: "unique-id"           # Required, unique across all levels
  level: 3                       # Required, 1-5
  skill: "distributive-inverse"  # Required, matches SKILL_BY_LEVEL
  kind: "diagnostic"             # Required: diagnostic, followup, practice, retest, check
  prompt: "LaTeX math string"    # Required, KaTeX-compatible
  options:                       # Required, array of option objects
    - id: "opt-1"                # Required, unique within item
      text: "LaTeX or plain"     # Required
      misconception_id: null     # null for correct, or misconception ID
      note: "Internal note"      # Optional, for content authors
  correct_option_id: "opt-1"     # Required, matches one option.id
  explanation: "LaTeX"           # Required, shown after answer
  discriminates: ["ID1", "ID2"]  # Required for diagnostic/followup/check
  targets: ["ID1"]               # Required for practice items
```

### Kind-Specific Rules

| Kind | Purpose | Min Count | Special Fields |
|------|---------|-----------|----------------|
| `diagnostic` | Initial assessment | 3/level | `discriminates` |
| `followup` | Discriminate hypotheses | 2/misconception | `discriminates` |
| `check` | Transfer (all-correct) | 2/level | `discriminates` |
| `practice` | Targeted practice | 6/level | `targets` |
| `retest` | Fresh assessment | 6/level | `discriminates` |

### Pool Sizes (Minimum)

| Level | Diagnostic | Follow-up | Check | Practice | Retest |
|-------|------------|-----------|-------|----------|--------|
| 1 | 4 | 2 | 2 | 6 | 6 |
| 2 | 4 | 3 | 2 | 6 | 6 |
| 3 | 4 | 4 | 2 | 6 | 6 |
| 4 | 4 | 4 | 2 | 6 | 6 |
| 5 | 4 | 4 | 2 | 6 | 6 |

**Level 3 (flagship) should exceed these minimums.**

### Disjointness Requirements

- Retest items MUST be disjoint from diagnostic/followup/check/practice pools
- Enforced in content verification tests
- Pool size ≥ 6 ensures fresh retests for multiple attempts

## Authoring Checklist

For each new item:

- [ ] Unique `item_id` (format: `{kind}-{level}-{skill}-{nn}`)
- [ ] Valid `level` (1-5) and `skill` (matches SKILL_BY_LEVEL)
- [ ] `prompt` renders in KaTeX (test with `npx katex-cli`)
- [ ] Exactly one correct option (`misconception_id: null`)
- [ ] All distractors have valid `misconception_id` or `ARITHMETIC_SLIP`/`UNCLEAR`
- [ ] No duplicate option texts
- [ ] No option mathematically equivalent to correct answer
- [ ] `discriminates` lists valid misconception IDs (for diagnostic/followup/check)
- [ ] `targets` lists valid misconception IDs (for practice)
- [ ] `explanation` is clear, non-judgmental, shows the mathematical step
- [ ] Correct option position randomized in content (not always first)

## Content Verification Tests

Run before committing content changes:

```bash
cd backend
pytest tests/test_content_verification.py -v
```

Tests verify:
1. **Sympy correctness**: Every correct answer recomputed and matches key
2. **Distractor procedures**: Each distractor with misconception_id has verifiable erroneous procedure
3. **Structure**: Unique IDs, correct option counts, no duplicate texts
4. **Position bias**: Correct options not biased toward first position
5. **Disjointness**: Retest pools disjoint from other kinds
6. **KaTeX rendering**: All prompts/options parse without errors
7. **Minimum counts**: Each level/kind meets minimum pool sizes

## Adding a New Level

1. Create `level{N}.yaml` in `backend/app/content/`
2. Add level info to `LEVEL_INFO` in `backend/app/api/levels.py`
3. Add skill mapping to `SKILL_BY_LEVEL` in same file
4. Add misconceptions relevant to the level
5. Create all 5 item kinds with minimum counts
6. Run content verification tests
7. Add level to frontend `LEVEL_INFO` in `LearningMap.tsx` and `Journey.tsx`

## LaTeX Guidelines

- Use KaTeX-compatible syntax (most LaTeX math mode works)
- Inline: `$x^2$` or `\(x^2\)` — but we use plain strings, KaTeX renders in math mode
- Display: `$$x^2$$` or `\[x^2\]`
- Common: `\times`, `\div`, `\frac{a}{b}`, `\sqrt{x}`, `\leq`, `\geq`, `\neq`
- Avoid: `\begin{align}`, `\text{}` (use plain text in options)
- Test: `npx katex-cli "your latex"` 

## Tone Guidelines

- **Never**: "You have the misconception...", "You failed...", "Mastered"
- **Always**: "Your answer is consistent with...", "One possible explanation...", "Evidence suggests..."
- Explanations: Show the mathematical step, not just the answer
- Feedback: "Not quite — this is useful information" not "Wrong"

## Content Review Process

1. Author creates/edits YAML
2. Run `pytest tests/test_content_verification.py`
3. Fix any failures
4. Peer review for mathematical accuracy and tone
5. Deploy to staging, run E2E smoke test
6. Merge to main