from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID, uuid4
from typing import Optional, List
import json
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import (
    Learner, Session as SessionModel, SessionPhase, SessionStatus,
    Item, ServedItem, Response, ResponseKind, Progress, SkillStatus,
    XPEvent, Achievement, Hypothesis, HypothesisStatus
)
from app.schemas import (
    SessionCreate, SessionOut, QuestionOut, AnswerIn, AnswerOut,
    FeedbackOut, OptionOut, ErrorOut
)
from app.api.learners import get_current_learner, hash_token
from app.engine.state_machine import DiagnosticEngine
from app.content.loader import get_content_loader
from app.engine.misconceptions import get_misconception, confidence_wording

router = APIRouter()


def get_engine():
    return DiagnosticEngine(get_content_loader())


@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_in: SessionCreate,
    learner: Learner = Depends(get_current_learner),
    db: Session = Depends(get_db)
):
    """Start a new diagnostic session for a level, or resume existing."""
    # Check for existing in-progress session for this level
    existing = db.query(SessionModel).filter(
        SessionModel.learner_id == learner.id,
        SessionModel.level == session_in.level,
        SessionModel.status == SessionStatus.IN_PROGRESS
    ).first()

    if existing:
        return SessionOut.model_validate(existing)

    # Create new session
    session = SessionModel(
        learner_id=learner.id,
        level=session_in.level,
        phase=SessionPhase.DIAGNOSTIC,
        step_index=0,
        status=SessionStatus.IN_PROGRESS,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.get("/sessions/{session_id}", response_model=QuestionOut)
async def get_current_question(
    session_id: UUID,
    learner: Learner = Depends(get_current_learner),
    db: Session = Depends(get_db)
):
    """Get the current question for a session."""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.learner_id == learner.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Session not in progress")

    # Get the next question from the engine
    engine = get_engine()

    # Reconstruct engine state from DB
    from app.engine.state_machine import EngineState, Phase
    from uuid import UUID as UUIDClass

    served_items_db = db.query(ServedItem).filter(ServedItem.session_id == session_id).all()
    responses_db = db.query(Response).filter(Response.session_id == session_id).all()
    hypotheses_db = db.query(Hypothesis).filter(Hypothesis.learner_id == learner.id).all()

    # Build engine state
    state = EngineState(
        session_id=session.id,
        learner_id=learner.id,
        level=session.level,
        phase=Phase(session.phase.value),
        step_index=session.step_index,
        current_skill=engine.content.get_primary_skill(session.level),
    )

    # Restore served items
    for si in served_items_db:
        item = db.query(Item).filter(Item.id == si.item_id).first()
        if item:
            from app.engine.state_machine import ServedQuestion
            served = ServedQuestion(
                item_id=item.item_id,
                served_item_id=si.id,
                prompt=item.prompt,
                options=json.loads(si.option_order),  # This should be the shuffled options
                option_order=json.loads(si.option_order),
                correct_option_id=item.correct_option_id,
                explanation=item.explanation,
                discriminates=json.loads(item.discriminates) if item.discriminates else [],
                step_index=session.step_index,
                total_steps=3,  # placeholder
                phase=Phase(session.phase.value),
                skill=engine.content.get_primary_skill(session.level),
            )
            state.served_items.append(served)

    # Restore responses
    for r in responses_db:
        state.responses.append({
            "served_item_id": str(r.served_item_id),
            "item_id": r.item_id,
            "chosen_option_id": r.chosen_option_id,
            "is_correct": r.is_correct,
            "misconception_id": r.misconception_id,
            "kind": r.kind.value,
            "phase": r.kind.value,
            "skill": engine.content.get_primary_skill(session.level),
            "result": {
                "is_correct": r.is_correct,
                "chosen_option_id": r.chosen_option_id,
                "misconception_id": r.misconception_id,
                "explanation": "",
                "step_note": None,
                "xp_awarded": 0,
            }
        })

    # Restore hypotheses
    for h in hypotheses_db:
        state.hypotheses[h.misconception_id] = {
            "score": h.evidence_score,
            "has_followup": h.evidence_score >= 4,  # rough heuristic
            "status": h.status.value,
        }

    # Get next question
    next_question = engine.get_next_question(state)

    if not next_question:
        # Session complete
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=409, detail="Session complete")

    # Save served item to DB if new
    existing_served = db.query(ServedItem).filter(
        ServedItem.session_id == session_id,
        ServedItem.item_id == db.query(Item).filter(Item.item_id == next_question.item_id).first().id
    ).first()

    if not existing_served:
        item = db.query(Item).filter(Item.item_id == next_question.item_id).first()
        served_item = ServedItem(
            session_id=session_id,
            item_id=item.id,
            option_order=json.dumps(next_question.option_order),
        )
        db.add(served_item)
        db.commit()
        next_question.served_item_id = served_item.id

    # Update session step
    session.step_index = next_question.step_index
    session.phase = SessionPhase(next_question.phase.value)
    db.commit()

    # Build response
    options_out = [OptionOut(id=opt["id"], text=opt["text"]) for opt in next_question.options]

    phase_labels = {
        Phase.DIAGNOSTIC: f"Diagnostic · Question {next_question.step_index + 1} of {next_question.total_steps}",
        Phase.FOLLOWUP: "Follow-up · Gathering evidence",
        Phase.CHECK_UNDERSTANDING: f"Check Understanding · Question {next_question.step_index + 1} of {next_question.total_steps}",
        Phase.PRACTICE: f"Targeted practice · Question {next_question.step_index + 1} of 3",
        Phase.RETEST: f"Fresh retest · Question {next_question.step_index + 1} of 3",
    }

    return QuestionOut(
        served_item_id=next_question.served_item_id,
        item_id=next_question.item_id,
        prompt=next_question.prompt,
        options=options_out,
        step_label=phase_labels.get(next_question.phase, "Question"),
        phase=next_question.phase,
        step_index=next_question.step_index,
        total_steps=next_question.total_steps,
    )


@router.post("/sessions/{session_id}/answer", response_model=AnswerOut)
async def submit_answer(
    session_id: UUID,
    answer_in: AnswerIn,
    learner: Learner = Depends(get_current_learner),
    db: Session = Depends(get_db)
):
    """Submit an answer and get feedback + next question."""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.learner_id == learner.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Session not in progress")

    # Check idempotency - has this served_item already been answered?
    existing_response = db.query(Response).filter(
        Response.session_id == session_id,
        Response.served_item_id == answer_in.served_item_id
    ).first()

    if existing_response:
        # Return cached result
        return _build_answer_out(existing_response, session, db, learner)

    # Get the served item
    served_item = db.query(ServedItem).filter(
        ServedItem.id == answer_in.served_item_id,
        ServedItem.session_id == session_id
    ).first()

    if not served_item:
        raise HTTPException(status_code=404, detail="Served item not found")

    item = db.query(Item).filter(Item.id == served_item.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Grade the answer
    is_correct = False
    misconception_id = None
    step_note = None

    if answer_in.option_id is None:
        # "I'm not sure"
        is_correct = False
        misconception_id = None
        step_note = None
    elif answer_in.option_id == item.correct_option_id:
        is_correct = True
        misconception_id = None
        step_note = None
    else:
        is_correct = False
        # Find misconception for this option
        options = json.loads(item.options)
        for opt in options:
            if opt["id"] == answer_in.option_id:
                misconception_id = opt.get("misconception_id")
                if misconception_id:
                    misc = get_misconception(misconception_id)
                    step_note = misc["step"]
                break

    # Determine XP award
    xp_awarded = 0
    kind = ResponseKind(session.phase.value)
    if kind == ResponseKind.PRACTICE:
        xp_awarded = 50
    elif kind == ResponseKind.RETEST:
        xp_awarded = 25

    # Award XP idempotently
    if xp_awarded > 0:
        event_key = f"{kind.value}:{session_id}"
        existing_xp = db.query(XPEvent).filter(XPEvent.event_key == event_key).first()
        if not existing_xp:
            xp_event = XPEvent(
                learner_id=learner.id,
                event_type=kind.value,
                event_key=event_key,
                xp_amount=xp_awarded,
            )
            db.add(xp_event)

    # Record response
    response = Response(
        learner_id=learner.id,
        session_id=session_id,
        item_id=item.id,
        served_item_id=served_item.id,
        chosen_option_id=answer_in.option_id,
        is_correct=1 if is_correct else 0,
        misconception_id=misconception_id,
        kind=kind,
        latency_ms=None,  # Could add from client
    )
    db.add(response)

    # Update hypotheses
    _update_hypotheses_db(db, learner.id, engine.content.get_primary_skill(session.level), response, item, session.phase)

    # Determine next phase
    engine = get_engine()
    next_phase = _determine_next_phase(session, response, engine, db)

    # Update session
    session.phase = next_phase
    if next_phase != session.phase:
        session.step_index = 0
    else:
        session.step_index += 1

    if next_phase == SessionPhase.COMPLETED:
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(timezone.utc)
        _finalize_progress(db, learner.id, session.level, engine.content.get_primary_skill(session.level), responses_db=db.query(Response).filter(Response.session_id == session_id).all())

    db.commit()

    # Get next question if not complete
    next_question = None
    if next_phase != SessionPhase.COMPLETED:
        next_q = _get_next_question_for_session(db, session_id, session, engine, learner)
        if next_q:
            next_question = next_q

    # Build feedback
    feedback = FeedbackOut(
        is_correct=is_correct,
        explanation=item.explanation,
        step_note=step_note,
        misconception_id=misconception_id,
        next_phase=next_phase,
        next_step_label=_get_phase_label(next_phase, session.step_index, 3),
        xp_awarded=xp_awarded,
    )

    return AnswerOut(
        feedback=feedback,
        next_question=next_question,
        session=SessionOut.model_validate(session),
    )


def _build_answer_out(response: Response, session: SessionModel, db: Session, learner: Learner) -> AnswerOut:
    """Build AnswerOut from existing response (for idempotency)."""
    item = db.query(Item).filter(Item.id == response.item_id).first()
    feedback = FeedbackOut(
        is_correct=bool(response.is_correct),
        explanation=item.explanation if item else "",
        step_note=None,
        misconception_id=response.misconception_id,
        next_phase=session.phase,
        next_step_label=_get_phase_label(session.phase, session.step_index, 3),
        xp_awarded=0,
    )
    return AnswerOut(feedback=feedback, next_question=None, session=SessionOut.model_validate(session))


def _determine_next_phase(session: SessionModel, response: Response, engine: DiagnosticEngine, db: Session) -> SessionPhase:
    """Determine next phase based on current phase and response."""
    current = session.phase

    if current == SessionPhase.DIAGNOSTIC:
        diagnostic_items = engine.content.get_diagnostic_items(session.level)
        if session.step_index + 1 < len(diagnostic_items):
            return SessionPhase.DIAGNOSTIC
        # Diagnostic complete
        if _has_potential_misconception(db, session.id):
            return SessionPhase.FOLLOWUP
        else:
            return SessionPhase.CHECK_UNDERSTANDING

    elif current == SessionPhase.FOLLOWUP:
        # For simplicity, one follow-up question
        return SessionPhase.PRACTICE

    elif current == SessionPhase.CHECK_UNDERSTANDING:
        check_items = engine.content.get_check_items(session.level)
        if session.step_index + 1 < len(check_items):
            return SessionPhase.CHECK_UNDERSTANDING
        return SessionPhase.PRACTICE

    elif current == SessionPhase.PRACTICE:
        if session.step_index + 1 < 3:
            return SessionPhase.PRACTICE
        return SessionPhase.RETEST

    elif current == SessionPhase.RETEST:
        if session.step_index + 1 < 3:
            return SessionPhase.RETEST
        return SessionPhase.COMPLETED

    return SessionPhase.COMPLETED


def _has_potential_misconception(db: Session, session_id: UUID) -> bool:
    """Check if diagnostic responses suggest any misconception."""
    responses = db.query(Response).filter(
        Response.session_id == session_id,
        Response.kind == ResponseKind.DIAGNOSTIC
    ).all()
    for r in responses:
        if r.misconception_id and r.misconception_id != "ARITHMETIC_SLIP":
            return True
    return False


def _get_next_question_for_session(db: Session, session_id: UUID, session: SessionModel, engine: DiagnosticEngine, learner: Learner):
    """Get next question for session based on phase."""
    from app.engine.state_machine import ServedQuestion, Phase
    import json

    if session.phase == SessionPhase.DIAGNOSTIC:
        items = engine.content.get_diagnostic_items(session.level)
        if session.step_index < len(items):
            item = items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, len(items), SessionPhase.DIAGNOSTIC, engine.content.get_primary_skill(session.level))

    elif session.phase == SessionPhase.FOLLOWUP:
        # Get top hypothesis
        hypotheses = db.query(Hypothesis).filter(Hypothesis.learner_id == learner.id).all()
        top_hyp = max(hypotheses, key=lambda h: h.evidence_score) if hypotheses else None
        if top_hyp:
            followup_items = engine.content.get_followup_items(session.level, top_hyp.misconception_id)
            if session.step_index < len(followup_items):
                item = followup_items[session.step_index]
                return _serve_item_db(db, session_id, item, session.step_index, len(followup_items), SessionPhase.FOLLOWUP, engine.content.get_primary_skill(session.level))

    elif session.phase == SessionPhase.CHECK_UNDERSTANDING:
        check_items = engine.content.get_check_items(session.level)
        if session.step_index < len(check_items):
            item = check_items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, len(check_items), SessionPhase.CHECK_UNDERSTANDING, engine.content.get_primary_skill(session.level))

    elif session.phase == SessionPhase.PRACTICE:
        hypotheses = db.query(Hypothesis).filter(Hypothesis.learner_id == learner.id).all()
        top_hyp = max(hypotheses, key=lambda h: h.evidence_score) if hypotheses else None
        responses = db.query(Response).filter(Response.session_id == session_id).all()
        practice_items = engine.content.get_practice_items(session.level, top_hyp.misconception_id if top_hyp else None, responses)
        if session.step_index < len(practice_items):
            item = practice_items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, min(3, len(practice_items)), SessionPhase.PRACTICE, engine.content.get_primary_skill(session.level))

    elif session.phase == SessionPhase.RETEST:
        seen_item_ids = {r.item_id for r in db.query(Response).filter(Response.session_id == session_id).all()}
        retest_items = engine.content.get_retest_items(session.level, engine.content.get_primary_skill(session.level), seen_item_ids)
        if session.step_index < len(retest_items):
            item = retest_items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, min(3, len(retest_items)), SessionPhase.RETEST, engine.content.get_primary_skill(session.level))

    return None


def _serve_item_db(db: Session, session_id: UUID, item: Item, step_index: int, total_steps: int, phase: SessionPhase, skill: str):
    """Create served item in DB and return QuestionOut."""
    import json
    import random

    options = json.loads(item.options)
    option_ids = [opt["id"] for opt in options]
    random.shuffle(option_ids)

    opt_map = {opt["id"]: opt for opt in options}
    shuffled_options = [{"id": oid, "text": opt_map[oid]["text"]} for oid in option_ids]

    served_item = ServedItem(
        session_id=session_id,
        item_id=item.id,
        option_order=json.dumps(shuffled_options),  # Store shuffled options
    )
    db.add(served_item)
    db.commit()
    db.refresh(served_item)

    options_out = [{"id": opt["id"], "text": opt["text"]} for opt in shuffled_options]

    phase_labels = {
        SessionPhase.DIAGNOSTIC: f"Diagnostic · Question {step_index + 1} of {total_steps}",
        SessionPhase.FOLLOWUP: "Follow-up · Gathering evidence",
        SessionPhase.CHECK_UNDERSTANDING: f"Check Understanding · Question {step_index + 1} of {total_steps}",
        SessionPhase.PRACTICE: f"Targeted practice · Question {step_index + 1} of 3",
        SessionPhase.RETEST: f"Fresh retest · Question {step_index + 1} of 3",
    }

    return QuestionOut(
        served_item_id=served_item.id,
        item_id=item.item_id,
        prompt=item.prompt,
        options=[{"id": o["id"], "text": o["text"]} for o in shuffled_options],
        step_label=phase_labels.get(phase, "Question"),
        phase=phase,
        step_index=step_index,
        total_steps=total_steps,
    )


def _update_hypotheses_db(db: Session, learner_id: UUID, skill: str, response: Response, item: Item, phase: SessionPhase):
    """Update hypothesis evidence scores based on response."""
    from app.engine.misconceptions import EVIDENCE_PARAMS

    params = EVIDENCE_PARAMS
    kind = response.kind.value
    misconception_id = response.misconception_id
    is_correct = bool(response.is_correct)

    if kind == "diagnostic" and misconception_id:
        _adjust_hypothesis(db, learner_id, skill, misconception_id, params["diagnostic_match"])

    elif kind == "followup":
        discriminates = json.loads(item.discriminates) if item.discriminates else []
        if misconception_id and misconception_id in discriminates:
            _adjust_hypothesis(db, learner_id, skill, misconception_id, params["followup_consistent"])
            # Mark has_followup
            hyp = db.query(Hypothesis).filter(
                Hypothesis.learner_id == learner_id,
                Hypothesis.skill == skill,
                Hypothesis.misconception_id == misconception_id
            ).first()
            if hyp:
                hyp.evidence_score += 0  # Just to trigger update
        elif is_correct and discriminates:
            for hyp_id in discriminates:
                _adjust_hypothesis(db, learner_id, skill, hyp_id, params["followup_contradicts"])

    elif kind in ("practice", "retest") and misconception_id:
        _adjust_hypothesis(db, learner_id, skill, misconception_id, params["practice_error"])

    # Recalculate statuses
    hypotheses = db.query(Hypothesis).filter(Hypothesis.learner_id == learner_id, Hypothesis.skill == skill).all()
    for hyp in hypotheses:
        runner_up = max([h.evidence_score for h in hypotheses if h != hyp], default=0)
        has_followup = hyp.evidence_score >= 4  # heuristic
        from app.engine.misconceptions import hypothesis_status
        hyp.status = HypothesisStatus(hypothesis_status(hyp.evidence_score, runner_up, has_followup))

    db.commit()


def _adjust_hypothesis(db: Session, learner_id: UUID, skill: str, misconception_id: str, delta: int):
    hyp = db.query(Hypothesis).filter(
        Hypothesis.learner_id == learner_id,
        Hypothesis.skill == skill,
        Hypothesis.misconception_id == misconception_id
    ).first()
    if not hyp:
        hyp = Hypothesis(
            learner_id=learner_id,
            skill=skill,
            misconception_id=misconception_id,
            evidence_score=0,
        )
        db.add(hyp)
    hyp.evidence_score += delta


def _finalize_progress(db: Session, learner_id: UUID, level: int, skill: str, responses_db: List[Response]):
    """Update progress record after session completion."""
    diagnostic_responses = [r for r in responses_db if r.kind == ResponseKind.DIAGNOSTIC]
    retest_responses = [r for r in responses_db if r.kind == ResponseKind.RETEST]

    diagnostic_correct = sum(1 for r in diagnostic_responses if r.is_correct)
    diagnostic_total = len(diagnostic_responses)
    retest_correct = sum(1 for r in retest_responses if r.is_correct)
    retest_total = len(retest_responses)

    progress = db.query(Progress).filter(Progress.learner_id == learner_id, Progress.skill == skill).first()
    if not progress:
        progress = Progress(learner_id=learner_id, skill=skill, level=level)
        db.add(progress)

    progress.last_retest_score = retest_correct
    progress.last_retest_total = retest_total
    progress.retest_count += 1

    if retest_total == 0:
        progress.status = SkillStatus.NOT_ASSESSED
    elif retest_correct >= 2:
        if progress.retest_count >= 2:
            progress.status = SkillStatus.CONSISTENT_EVIDENCE
        else:
            progress.status = SkillStatus.ENCOURAGING_EVIDENCE
    else:
        progress.status = SkillStatus.NEEDS_MORE_PRACTICE

    # Check for achievements
    if progress.retest_count == 1 and retest_correct >= 2:
        ach = db.query(Achievement).filter(
            Achievement.learner_id == learner_id,
            Achievement.achievement_id == "first-retest"
        ).first()
        if not ach:
            db.add(Achievement(learner_id=learner_id, achievement_id="first-retest"))

    if diagnostic_total > 0 and progress.retest_count == 1:
        ach = db.query(Achievement).filter(
            Achievement.learner_id == learner_id,
            Achievement.achievement_id == "first-practice"
        ).first()
        if not ach:
            db.add(Achievement(learner_id=learner_id, achievement_id="first-practice"))

    db.commit()


def _get_phase_label(phase: SessionPhase, step_index: int, total: int) -> str:
    labels = {
        SessionPhase.DIAGNOSTIC: f"Diagnostic · Question {step_index + 1} of {total}",
        SessionPhase.FOLLOWUP: "Follow-up · Gathering evidence",
        SessionPhase.CHECK_UNDERSTANDING: f"Check Understanding · Question {step_index + 1} of {total}",
        SessionPhase.PRACTICE: f"Targeted practice · Question {step_index + 1} of 3",
        SessionPhase.RETEST: f"Fresh retest · Question {step_index + 1} of 3",
        SessionPhase.RESULTS: "Results",
        SessionPhase.COMPLETED: "Completed",
    }
    return labels.get(phase, "Question")