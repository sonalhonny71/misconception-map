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

    engine = get_engine()

    next_question = _next_question_or_advance(db, session, engine, learner)

    if not next_question:
        # Nothing left to ask: the session is complete
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=409, detail="Session complete")

    return next_question


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

    # Check idempotency - has this served_item already been answered?
    existing_response = db.query(Response).filter(
        Response.session_id == session_id,
        Response.served_item_id == answer_in.served_item_id
    ).first()

    if existing_response:
        # Return cached result
        return _build_answer_out(existing_response, session, db, learner)

    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="Session not in progress")

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

    engine = get_engine()
    skill = engine.content.get_primary_skill(session.level)

    # The session phase "check_understanding" is stored as response kind "check"
    kind = _KIND_BY_PHASE[session.phase]

    # Determine XP award (once per session and phase, so retries never double-award)
    xp_awarded = 0
    potential_xp = 50 if kind == ResponseKind.PRACTICE else 25 if kind == ResponseKind.RETEST else 0
    if potential_xp > 0:
        event_key = f"{kind.value}:{session_id}"
        existing_xp = db.query(XPEvent).filter(XPEvent.event_key == event_key).first()
        if not existing_xp:
            db.add(XPEvent(
                learner_id=learner.id,
                event_type=kind.value,
                event_key=event_key,
                xp_amount=potential_xp,
            ))
            xp_awarded = potential_xp

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
    db.flush()

    # Update hypotheses
    _update_hypotheses_db(db, learner.id, skill, response, item, session.phase)

    # Determine next phase
    previous_phase = session.phase
    next_phase = _determine_next_phase(session, response, engine, db)

    # Update session: a new phase starts again at step 0
    session.phase = next_phase
    if next_phase != previous_phase:
        session.step_index = 0
    else:
        session.step_index += 1

    if next_phase == SessionPhase.COMPLETED:
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.now(timezone.utc)
        _finalize_progress(db, learner.id, session.level, skill, responses_db=db.query(Response).filter(Response.session_id == session_id).all())

    db.commit()

    # Get next question if not complete
    next_question = None
    if next_phase != SessionPhase.COMPLETED:
        next_question = _next_question_or_advance(db, session, engine, learner)
        if next_question is None:
            session.status = SessionStatus.COMPLETED
            session.ended_at = datetime.now(timezone.utc)
            _finalize_progress(db, learner.id, session.level, skill, responses_db=db.query(Response).filter(Response.session_id == session_id).all())
            db.commit()

    # Build feedback
    feedback = FeedbackOut(
        is_correct=is_correct,
        explanation=item.explanation,
        step_note=step_note,
        misconception_id=misconception_id,
        next_phase=next_phase,
        next_step_label=next_question.step_label if next_question else _get_phase_label(session.phase, session.step_index, 3),
        xp_awarded=xp_awarded,
        correct_option_id=item.correct_option_id,
    )

    return AnswerOut(
        feedback=feedback,
        next_question=next_question,
        session=SessionOut.model_validate(session),
    )


def _build_answer_out(response: Response, session: SessionModel, db: Session, learner: Learner) -> AnswerOut:
    """Rebuild the AnswerOut for an answer that was already recorded (idempotent re-submit)."""
    item = db.query(Item).filter(Item.id == response.item_id).first()

    step_note = None
    if response.misconception_id:
        step_note = get_misconception(response.misconception_id)["step"]

    # XP is awarded once per session and phase, on the first answer of that phase
    xp_awarded = 0
    if response.kind in (ResponseKind.PRACTICE, ResponseKind.RETEST):
        first_response = db.query(Response).filter(
            Response.session_id == response.session_id,
            Response.kind == response.kind,
        ).order_by(Response.created_at, Response.id).first()
        if first_response is not None and first_response.id == response.id:
            event = db.query(XPEvent).filter(
                XPEvent.event_key == f"{response.kind.value}:{response.session_id}"
            ).first()
            xp_awarded = event.xp_amount if event else 0

    next_question = None
    if session.status == SessionStatus.IN_PROGRESS:
        next_question = _next_question_or_advance(db, session, get_engine(), learner)

    feedback = FeedbackOut(
        is_correct=bool(response.is_correct),
        explanation=item.explanation if item else "",
        step_note=step_note,
        misconception_id=response.misconception_id,
        next_phase=session.phase,
        next_step_label=next_question.step_label if next_question else _get_phase_label(session.phase, session.step_index, 3),
        xp_awarded=xp_awarded,
        correct_option_id=item.correct_option_id if item else None,
    )
    return AnswerOut(feedback=feedback, next_question=next_question, session=SessionOut.model_validate(session))


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


_KIND_BY_PHASE = {
    SessionPhase.DIAGNOSTIC: ResponseKind.DIAGNOSTIC,
    SessionPhase.FOLLOWUP: ResponseKind.FOLLOWUP,
    SessionPhase.CHECK_UNDERSTANDING: ResponseKind.CHECK,
    SessionPhase.PRACTICE: ResponseKind.PRACTICE,
    SessionPhase.RETEST: ResponseKind.RETEST,
}


def _item_ids_seen_in_other_phases(db: Session, session_id: UUID, phase: SessionPhase) -> set:
    """Logical item ids already answered in this session in a *different* phase.

    Practice and retest questions must be fresh, but the list for the current phase
    has to stay stable while the learner moves through it.
    """
    rows = (
        db.query(Item.item_id, Response.kind)
        .join(Response, Response.item_id == Item.id)
        .filter(Response.session_id == session_id)
        .all()
    )
    current_kind = _KIND_BY_PHASE.get(phase)
    return {item_id for item_id, kind in rows if kind != current_kind}


def _next_question_or_advance(db: Session, session: SessionModel, engine: DiagnosticEngine, learner: Learner):
    """Return the question for the session's current step.

    If a phase has no questions at all (for example no follow-up exists for the
    leading hypothesis), move on to practice instead of getting stuck.
    """
    question = _get_next_question_for_session(db, session.id, session, engine, learner)
    if question is None and session.phase in (SessionPhase.FOLLOWUP, SessionPhase.CHECK_UNDERSTANDING):
        session.phase = SessionPhase.PRACTICE
        session.step_index = 0
        db.commit()
        question = _get_next_question_for_session(db, session.id, session, engine, learner)
    return question


def _get_next_question_for_session(db: Session, session_id: UUID, session: SessionModel, engine: DiagnosticEngine, learner: Learner):
    """Get next question for session based on phase."""
    skill = engine.content.get_primary_skill(session.level)

    if session.phase == SessionPhase.DIAGNOSTIC:
        items = engine.content.get_diagnostic_items(session.level)
        if session.step_index < len(items):
            item = items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, len(items), SessionPhase.DIAGNOSTIC, skill)

    elif session.phase == SessionPhase.FOLLOWUP:
        # Get top hypothesis
        hypotheses = db.query(Hypothesis).filter(Hypothesis.learner_id == learner.id).all()
        top_hyp = max(hypotheses, key=lambda h: h.evidence_score) if hypotheses else None
        if top_hyp:
            followup_items = engine.content.get_followup_items(session.level, top_hyp.misconception_id)
            if session.step_index < len(followup_items):
                item = followup_items[session.step_index]
                return _serve_item_db(db, session_id, item, session.step_index, len(followup_items), SessionPhase.FOLLOWUP, skill)

    elif session.phase == SessionPhase.CHECK_UNDERSTANDING:
        check_items = engine.content.get_check_items(session.level)
        if session.step_index < len(check_items):
            item = check_items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, len(check_items), SessionPhase.CHECK_UNDERSTANDING, skill)

    elif session.phase == SessionPhase.PRACTICE:
        hypotheses = db.query(Hypothesis).filter(Hypothesis.learner_id == learner.id).all()
        top_hyp = max(hypotheses, key=lambda h: h.evidence_score) if hypotheses else None
        seen = [{"item_id": i} for i in _item_ids_seen_in_other_phases(db, session_id, SessionPhase.PRACTICE)]
        practice_items = engine.content.get_practice_items(session.level, top_hyp.misconception_id if top_hyp else None, seen)
        if session.step_index < min(3, len(practice_items)):
            item = practice_items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, min(3, len(practice_items)), SessionPhase.PRACTICE, skill)

    elif session.phase == SessionPhase.RETEST:
        seen_item_ids = _item_ids_seen_in_other_phases(db, session_id, SessionPhase.RETEST)
        retest_items = engine.content.get_retest_items(session.level, skill, seen_item_ids)
        if session.step_index < min(3, len(retest_items)):
            item = retest_items[session.step_index]
            return _serve_item_db(db, session_id, item, session.step_index, min(3, len(retest_items)), SessionPhase.RETEST, skill)

    return None


def _serve_item_db(db: Session, session_id: UUID, item_data: dict, step_index: int, total_steps: int, phase: SessionPhase, skill: str):
    """Serve a content item: create (or re-use) its ServedItem row and return the QuestionOut.

    Re-using the row means refreshing the page shows the same question with the
    same option order, and the answer can be matched to what was displayed.
    """
    import random

    item = db.query(Item).filter(Item.item_id == item_data["item_id"]).first()
    if item is None:
        raise HTTPException(
            status_code=500,
            detail=f"Content item {item_data['item_id']} is missing from the database (run the content seed).",
        )

    options = json.loads(item.options)
    opt_map = {opt["id"]: opt for opt in options}

    served_item = db.query(ServedItem).filter(
        ServedItem.session_id == session_id,
        ServedItem.item_id == item.id,
    ).first()

    if served_item is None:
        option_ids = [opt["id"] for opt in options]
        random.shuffle(option_ids)
        served_item = ServedItem(
            session_id=session_id,
            item_id=item.id,
            option_order=json.dumps(option_ids),  # option IDs in the order shown
        )
        db.add(served_item)
        db.commit()
        db.refresh(served_item)

    option_ids = json.loads(served_item.option_order)

    return QuestionOut(
        served_item_id=served_item.id,
        item_id=item.item_id,
        prompt=item.prompt,
        options=[OptionOut(id=oid, text=opt_map[oid]["text"]) for oid in option_ids],
        step_label=_get_phase_label(phase, step_index, total_steps),
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

    # Recalculate statuses (flush first so brand-new hypotheses are included)
    db.flush()
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
        progress = Progress(learner_id=learner_id, skill=skill, level=level, retest_count=0)
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