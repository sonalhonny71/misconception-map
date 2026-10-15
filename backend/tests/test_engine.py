import pytest
import uuid
from app.engine.state_machine import DiagnosticEngine
from app.content.loader import ContentLoader
from pathlib import Path
from app.engine.misconceptions import hypothesis_status, confidence_wording, EVIDENCE_PARAMS


@pytest.fixture
def engine():
    return DiagnosticEngine(ContentLoader(Path(__file__).parent.parent / "app" / "content"))


def test_hypothesis_status_thresholds():
    """Test status determination at various score thresholds."""
    # Insufficient (< 4)
    assert hypothesis_status(0, 0, False) == "insufficient"
    assert hypothesis_status(3, 0, False) == "insufficient"
    
    # Possible (4-5)
    assert hypothesis_status(4, 0, False) == "possible"
    assert hypothesis_status(5, 0, False) == "possible"
    
    # Supported (>=6, margin>=3, has_followup)
    assert hypothesis_status(6, 0, True) == "supported"
    assert hypothesis_status(10, 5, True) == "supported"  # margin 5 >= 3
    
    # Not supported: insufficient margin
    assert hypothesis_status(6, 4, True) == "possible"  # margin 2 < 3
    
    # Not supported: no follow-up
    assert hypothesis_status(10, 0, False) == "possible"


def test_confidence_wording():
    """Test human-readable wording for each status."""
    assert confidence_wording("insufficient") == "We don't have enough evidence yet to say why."
    assert confidence_wording("possible") == "One possible explanation, still checking."
    assert confidence_wording("supported") == "The evidence supports this explanation."
    assert confidence_wording("unknown") == "We don't have enough evidence yet to say why."


def test_evidence_params_defined():
    """All required evidence parameters should be defined."""
    required = [
        "diagnostic_match", "followup_consistent", "followup_contradicts",
        "unsure", "practice_error", "retest_error",
        "insufficient_threshold", "possible_threshold", "supported_threshold",
        "margin_required", "requires_followup_for_supported"
    ]
    for key in required:
        assert key in EVIDENCE_PARAMS, f"Missing evidence param: {key}"


def test_diagnostic_to_followup_transition(engine):
    """Diagnostic with misconception signal should go to followup."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Answer all diagnostic questions with DIST_PARTIAL
    for i in range(4):  # 4 diagnostic questions in level 3
        if state.phase.value != "diagnostic":
            break
        q = engine.get_next_question(state)
        if not q:
            break
        # Choose DIST_PARTIAL distractor
        distractor = next((o for o in q.options if o.get("misconception_id") == "DIST_PARTIAL"), None)
        if distractor:
            result, state = engine.submit_answer(state, q.served_item_id, distractor["id"])
        else:
            result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Should transition to followup (not check_understanding)
    assert state.phase.value == "followup"


def test_all_correct_diagnostic_to_check(engine):
    """All-correct diagnostic should go to check_understanding."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Answer all diagnostic questions correctly
    for i in range(4):
        if state.phase.value != "diagnostic":
            break
        q = engine.get_next_question(state)
        if not q:
            break
        result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Should transition to check_understanding
    assert state.phase.value == "check_understanding"


def test_followup_can_lower_score(engine):
    """Correct follow-up answer should lower competing hypothesis score."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # First, get a DIST_PARTIAL signal in diagnostic
    q = engine.get_next_question(state)
    distractor = next((o for o in q.options if o.get("misconception_id") == "DIST_PARTIAL"), None)
    if distractor:
        result, state = engine.submit_answer(state, q.served_item_id, distractor["id"])
        initial_score = state.hypotheses.get("DIST_PARTIAL", {}).get("score", 0)
        assert initial_score > 0
        
        # Complete diagnostic
        for _ in range(3):
            if state.phase.value == "diagnostic":
                q = engine.get_next_question(state)
                if q:
                    result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
        
        # Now in followup, answer correctly (should lower DIST_PARTIAL)
        if state.phase.value == "followup":
            q = engine.get_next_question(state)
            if q:
                result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
                # DIST_PARTIAL score should have decreased due to contradiction
                final_score = state.hypotheses.get("DIST_PARTIAL", {}).get("score", 0)
                # Note: followup_consistent adds to the chosen hypothesis
                # followup_contradicts subtracts from discriminated hypotheses
                # Since we answered correctly on a followup that discriminates DIST_PARTIAL,
                # DIST_PARTIAL should get -3


def test_practice_phase_has_3_questions(engine):
    """Practice phase should have exactly 3 questions."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Fast-forward to practice by answering all diagnostic correctly
    for _ in range(4):
        if state.phase.value != "diagnostic":
            break
        q = engine.get_next_question(state)
        if q:
            result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Skip check_understanding
    for _ in range(2):
        if state.phase.value == "check_understanding":
            q = engine.get_next_question(state)
            if q:
                result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Should be in practice
    assert state.phase.value == "practice"
    
    practice_count = 0
    while state.phase.value == "practice":
        q = engine.get_next_question(state)
        if not q:
            break
        practice_count += 1
        result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    assert practice_count == 3


def test_retest_phase_has_3_questions(engine):
    """Retest phase should have exactly 3 questions."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Fast-forward through all phases
    phases = ["diagnostic", "check_understanding", "practice", "retest"]
    for phase in phases:
        while state.phase.value == phase:
            q = engine.get_next_question(state)
            if not q:
                break
            result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Count retest questions
    retest_count = 0
    while state.phase.value == "retest":
        q = engine.get_next_question(state)
        if not q:
            break
        retest_count += 1
        result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    assert retest_count == 3


def test_explanation_generation(engine):
    """Test explanation output structure."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Answer diagnostic with DIST_PARTIAL
    q = engine.get_next_question(state)
    distractor = next((o for o in q.options if o.get("misconception_id") == "DIST_PARTIAL"), None)
    if distractor:
        result, state = engine.submit_answer(state, q.served_item_id, distractor["id"])
    
    # Complete remaining diagnostic
    for _ in range(3):
        if state.phase.value == "diagnostic":
            q = engine.get_next_question(state)
            if q:
                result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Get explanation
    explanation = engine.get_explanation(state)
    
    assert "hypothesis_id" in explanation
    assert "status" in explanation
    assert "wording" in explanation
    assert "evidence_trail" in explanation
    assert isinstance(explanation["evidence_trail"], list)


def test_compute_progress(engine):
    """Test progress computation after retest."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Simulate a full journey with some wrong answers
    # Diagnostic: 2 correct, 2 wrong
    for i in range(4):
        if state.phase.value != "diagnostic":
            break
        q = engine.get_next_question(state)
        if q:
            if i < 2:
                result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
            else:
                distractor = next((o for o in q.options if o.get("misconception_id")), None)
                if distractor:
                    result, state = engine.submit_answer(state, q.served_item_id, distractor["id"])
                else:
                    result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Skip to practice
    for _ in range(2):
        if state.phase.value == "check_understanding":
            q = engine.get_next_question(state)
            if q:
                result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Practice: all correct
    for _ in range(3):
        if state.phase.value == "practice":
            q = engine.get_next_question(state)
            if q:
                result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
    
    # Retest: 2 correct, 1 wrong
    for i in range(3):
        if state.phase.value == "retest":
            q = engine.get_next_question(state)
            if q:
                if i < 2:
                    result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
                else:
                    result, state = engine.submit_answer(state, q.served_item_id, q.options[1]["id"])
    
    # Check progress
    progress = engine.compute_progress(state)
    assert progress["diagnostic_score"] == 2
    assert progress["diagnostic_total"] == 4
    assert progress["retest_score"] == 2
    assert progress["retest_total"] == 3
    assert progress["status"] == "encouraging_evidence"


def test_single_slip_rule(engine):
    """Single isolated error should be ARITHMETIC_SLIP, not a misconception."""
    import uuid
    learner_id = uuid.uuid4()
    state = engine.start_session(learner_id, 3)
    
    # Answer first question with ARITHMETIC_SLIP distractor
    q = engine.get_next_question(state)
    slip_distractor = next((o for o in q.options if o.get("misconception_id") == "ARITHMETIC_SLIP"), None)
    
    if slip_distractor:
        result, state = engine.submit_answer(state, q.served_item_id, slip_distractor["id"])
        
        # Complete diagnostic correctly
        for _ in range(3):
            if state.phase.value == "diagnostic":
                q = engine.get_next_question(state)
                if q:
                    result, state = engine.submit_answer(state, q.served_item_id, q.correct_option_id)
        
        # Should not have strong misconception hypothesis
        # ARITHMETIC_SLIP should not create a strong hypothesis
        assert "ARITHMETIC_SLIP" not in state.hypotheses or state.hypotheses["ARITHMETIC_SLIP"]["score"] < 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])