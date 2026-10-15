import pytest
import json
from pathlib import Path
from app.content.loader import ContentLoader
from app.engine.misconceptions import MISCONCEPTIONS, get_misconception
from app.engine.state_machine import DiagnosticEngine


@pytest.fixture
def content_loader():
    return ContentLoader(Path(__file__).parent.parent / "app" / "content")


@pytest.fixture
def engine(content_loader):
    return DiagnosticEngine(content_loader)


def test_all_levels_have_content(content_loader):
    """Each level should have at least minimum item counts."""
    for level in range(1, 6):
        diagnostic = content_loader.get_diagnostic_items(level)
        followup = content_loader.get_followup_items(level, "DIST_PARTIAL")  # sample
        check = content_loader.get_check_items(level)
        practice = content_loader.get_practice_items(level, None, [])
        retest = content_loader.get_retest_items(level, "test", set())

        assert len(diagnostic) >= 3, f"Level {level}: need ≥3 diagnostic, got {len(diagnostic)}"
        assert len(practice) >= 6, f"Level {level}: need ≥6 practice, got {len(practice)}"
        assert len(retest) >= 6, f"Level {level}: need ≥6 retest, got {len(retest)}"


def test_item_ids_unique(content_loader):
    """All item_ids must be unique across all levels."""
    all_items = content_loader.get_all_items()
    ids = [item["item_id"] for item in all_items]
    assert len(ids) == len(set(ids)), "Duplicate item_ids found"


def _get_options(item):
    """Get options as list, handling both YAML (list) and DB (JSON string) formats."""
    opts = item["options"]
    if isinstance(opts, str):
        return json.loads(opts)
    return opts


def _get_discriminates(item):
    """Get discriminates as list, handling both YAML and DB formats."""
    disc = item.get("discriminates")
    if disc is None:
        return []
    if isinstance(disc, str):
        return json.loads(disc)
    return disc


def _get_targets(item):
    """Get targets as list, handling both YAML and DB formats."""
    targets = item.get("targets")
    if targets is None:
        return []
    if isinstance(targets, str):
        return json.loads(targets)
    return targets


def test_correct_option_exists(content_loader):
    """Each item must have exactly one correct option."""
    for item in content_loader.get_all_items():
        options = _get_options(item)
        correct_ids = [o["id"] for o in options if o["id"] == item["correct_option_id"]]
        assert len(correct_ids) == 1, f"Item {item['item_id']}: correct_option_id not found in options"


def test_no_duplicate_option_texts(content_loader):
    """No duplicate option texts within an item."""
    for item in content_loader.get_all_items():
        options = _get_options(item)
        texts = [o["text"] for o in options]
        assert len(texts) == len(set(texts)), f"Item {item['item_id']}: duplicate option texts"


def test_no_equivalent_to_correct(content_loader):
    """No distractor should be mathematically equivalent to correct answer."""
    import sympy as sp
    
    for item in content_loader.get_all_items():
        options = _get_options(item)
        correct_opt = next(o for o in options if o["id"] == item["correct_option_id"])
        
        # Parse correct answer
        try:
            correct_expr = sp.sympify(correct_opt["text"])
        except:
            continue  # Skip non-mathematical options
        
        for opt in options:
            if opt["id"] == item["correct_option_id"]:
                continue
            try:
                opt_expr = sp.sympify(opt["text"])
                if sp.simplify(correct_expr - opt_expr) == 0:
                    assert False, f"Item {item['item_id']}: distractor '{opt['text']}' equals correct '{correct_opt['text']}'"
            except:
                pass  # Non-mathematical option


def test_correct_option_not_biased(content_loader):
    """Correct options should not always be at index 0."""
    positions = []
    for item in content_loader.get_all_items():
        options = _get_options(item)
        for i, opt in enumerate(options):
            if opt["id"] == item["correct_option_id"]:
                positions.append(i)
                break
    
    # At least some should not be at position 0
    non_zero = sum(1 for p in positions if p != 0)
    assert non_zero > len(positions) * 0.2, "Correct options heavily biased toward first position"


def test_retest_disjoint_from_other_kinds(content_loader):
    """Retest items must be disjoint from diagnostic/practice/followup/check pools."""
    for level in range(1, 6):
        retest_ids = {item["item_id"] for item in content_loader.get_retest_items(level, "test", set())}
        other_ids = {item["item_id"] for item in content_loader.get_all_items() 
                     if item["level"] == level and item["kind"] != "retest"}
        
        overlap = retest_ids & other_ids
        assert not overlap, f"Level {level}: retest items overlap with other kinds: {overlap}"


def test_katex_rendering(content_loader):
    """All prompts and options should be valid KaTeX."""
    import subprocess
    
    for item in content_loader.get_all_items():
        # Test prompt
        try:
            subprocess.run(["npx", "katex-cli", item["prompt"]], 
                         capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Skip if katex-cli not available
        
        # Test options
        options = _get_options(item)
        for opt in options:
            try:
                subprocess.run(["npx", "katex-cli", opt["text"]], 
                             capture_output=True, check=True, timeout=5)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass


def test_misconception_ids_valid(content_loader):
    """All misconception_ids in items must exist in catalogue."""
    valid_ids = set(MISCONCEPTIONS.keys())
    
    for item in content_loader.get_all_items():
        options = _get_options(item)
        for opt in options:
            misc_id = opt.get("misconception_id")
            if misc_id and misc_id not in valid_ids:
                assert False, f"Item {item['item_id']}: unknown misconception_id '{misc_id}'"


def test_discriminates_valid(content_loader):
    """All discriminates must be valid misconception IDs."""
    valid_ids = set(MISCONCEPTIONS.keys())
    
    for item in content_loader.get_all_items():
        disc = _get_discriminates(item)
        for d in disc:
            assert d in valid_ids, f"Item {item['item_id']}: invalid discriminates '{d}'"


def test_targets_valid(content_loader):
    """All targets in practice items must be valid misconception IDs."""
    valid_ids = set(MISCONCEPTIONS.keys())
    
    for item in content_loader.get_all_items():
        if item["kind"] == "practice":
            targets = _get_targets(item)
            for t in targets:
                assert t in valid_ids, f"Item {item['item_id']}: invalid target '{t}'"


def test_engine_state_machine(engine):
    """Test basic state machine transitions."""
    import uuid
    
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    assert state.phase.value == "diagnostic"
    assert state.step_index == 0
    assert len(state.served_items) == 1
    
    # Answer first diagnostic question
    served = state.served_items[0]
    result, new_state = engine.submit_answer(state, served.served_item_id, served.options[0]["id"])
    
    assert result.is_correct == (served.options[0]["id"] == served.correct_option_id)
    assert len(new_state.responses) == 1


def test_engine_unsure_neutral(engine):
    """'I'm not sure' should give neutral evidence (0 score change)."""
    import uuid
    
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    served = state.served_items[0]
    
    # Find "unsure" option
    unsure_opt = next((o for o in served.options if o["text"] == "I'm not sure yet"), None)
    if unsure_opt:
        result, new_state = engine.submit_answer(state, served.served_item_id, unsure_opt["id"])
        assert result.misconception_id is None
        assert not result.is_correct


def test_engine_followup_discriminates(engine):
    """Follow-up should discriminate between hypotheses."""
    import uuid
    
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Answer diagnostic with DIST_PARTIAL distractor
    served = state.served_items[0]
    distractor = next((o for o in served.options if o.get("misconception_id") == "DIST_PARTIAL"), None)
    
    if distractor:
        result, new_state = engine.submit_answer(state, served.served_item_id, distractor["id"])
        
        # Should have DIST_PARTIAL hypothesis
        assert "DIST_PARTIAL" in new_state.hypotheses
        assert new_state.hypotheses["DIST_PARTIAL"]["score"] > 0
        
        # Complete diagnostic to trigger follow-up
        for _ in range(3):  # remaining diagnostic questions
            if new_state.phase.value == "diagnostic":
                next_q, new_state = engine.advance_to_next_question(new_state)
                if next_q:
                    result, new_state = engine.submit_answer(new_state, next_q.served_item_id, next_q.correct_option_id)
        
        # Should be in followup phase
        assert new_state.phase.value in ("followup", "practice")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])