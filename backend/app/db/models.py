import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, UniqueConstraint, Index, Text, Integer, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


class SessionPhase(str, enum.Enum):
    DIAGNOSTIC = "diagnostic"
    FOLLOWUP = "followup"
    CHECK_UNDERSTANDING = "check_understanding"
    PRACTICE = "practice"
    RETEST = "retest"
    RESULTS = "results"
    COMPLETED = "completed"


class SessionStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ResponseKind(str, enum.Enum):
    DIAGNOSTIC = "diagnostic"
    FOLLOWUP = "followup"
    CHECK = "check"
    PRACTICE = "practice"
    RETEST = "retest"


class HypothesisStatus(str, enum.Enum):
    INSUFFICIENT = "insufficient"
    POSSIBLE = "possible"
    SUPPORTED = "supported"


class SkillStatus(str, enum.Enum):
    NOT_ASSESSED = "not_assessed"
    EVIDENCE_OF_DIFFICULTY = "evidence_of_difficulty"
    PRACTICING = "practicing"
    ENCOURAGING_EVIDENCE = "encouraging_evidence"
    CONSISTENT_EVIDENCE = "consistent_evidence"
    NEEDS_MORE_PRACTICE = "needs_more_practice"


class Learner(Base):
    __tablename__ = "learners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    sessions = relationship("Session", back_populates="learner", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="learner", cascade="all, delete-orphan")
    hypotheses = relationship("Hypothesis", back_populates="learner", cascade="all, delete-orphan")
    progress = relationship("Progress", back_populates="learner", cascade="all, delete-orphan")
    xp_events = relationship("XPEvent", back_populates="learner", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="learner", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(Integer, nullable=False)
    phase = Column(SQLEnum(SessionPhase), default=SessionPhase.DIAGNOSTIC, nullable=False)
    step_index = Column(Integer, default=0, nullable=False)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.IN_PROGRESS, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    learner = relationship("Learner", back_populates="sessions")
    responses = relationship("Response", back_populates="session", cascade="all, delete-orphan")
    served_items = relationship("ServedItem", back_populates="session", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(String(64), unique=True, nullable=False, index=True)  # e.g., "diag-3-dist-01"
    level = Column(Integer, nullable=False)
    skill = Column(String(64), nullable=False)
    kind = Column(String(32), nullable=False)  # diagnostic, followup, practice, retest, check
    prompt = Column(Text, nullable=False)  # LaTeX
    options = Column(Text, nullable=False)  # JSON: [{"id": "opt-1", "text": "...", "misconception_id": "...", "note": "..."}]
    correct_option_id = Column(String(64), nullable=False)
    explanation = Column(Text, nullable=False)
    discriminates = Column(Text, nullable=True)  # JSON array of misconception IDs
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    served_items = relationship("ServedItem", back_populates="item")
    responses = relationship("Response", back_populates="item")


class ServedItem(Base):
    __tablename__ = "served_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    option_order = Column(Text, nullable=False)  # JSON array of option IDs in the order shown
    served_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("Session", back_populates="served_items")
    item = relationship("Item", back_populates="served_items")
    responses = relationship("Response", back_populates="served_item")


class Response(Base):
    __tablename__ = "responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    served_item_id = Column(UUID(as_uuid=True), ForeignKey("served_items.id", ondelete="CASCADE"), nullable=False, unique=True)
    chosen_option_id = Column(String(64), nullable=True)  # null if "unsure"
    is_correct = Column(Integer, default=0, nullable=False)  # 0 or 1
    misconception_id = Column(String(64), nullable=True)
    kind = Column(SQLEnum(ResponseKind), nullable=False)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    learner = relationship("Learner", back_populates="responses")
    session = relationship("Session", back_populates="responses")
    item = relationship("Item", back_populates="responses")
    served_item = relationship("ServedItem", back_populates="responses")

    __table_args__ = (
        UniqueConstraint("session_id", "served_item_id", name="uq_session_served_item"),
        Index("ix_responses_learner_kind", "learner_id", "kind"),
    )


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    skill = Column(String(64), nullable=False, index=True)
    misconception_id = Column(String(64), nullable=False, index=True)
    evidence_score = Column(Integer, default=0, nullable=False)  # multiplied by 2 to store half-points
    status = Column(SQLEnum(HypothesisStatus), default=HypothesisStatus.INSUFFICIENT, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    learner = relationship("Learner", back_populates="hypotheses")

    __table_args__ = (
        UniqueConstraint("learner_id", "skill", "misconception_id", name="uq_learner_skill_misconception"),
    )


class Progress(Base):
    __tablename__ = "progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    skill = Column(String(64), nullable=False, index=True)
    level = Column(Integer, nullable=False)
    status = Column(SQLEnum(SkillStatus), default=SkillStatus.NOT_ASSESSED, nullable=False)
    last_retest_score = Column(Integer, nullable=True)
    last_retest_total = Column(Integer, nullable=True)
    retest_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    learner = relationship("Learner", back_populates="progress")

    __table_args__ = (
        UniqueConstraint("learner_id", "skill", name="uq_learner_skill"),
    )


class XPEvent(Base):
    __tablename__ = "xp_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)  # practice, retest, etc.
    event_key = Column(String(128), nullable=False, unique=True)  # e.g., "practice:session-uuid"
    xp_amount = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    learner = relationship("Learner", back_populates="xp_events")


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id = Column(String(64), nullable=False)  # e.g., "first-practice", "first-retest"
    earned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    learner = relationship("Learner", back_populates="achievements")

    __table_args__ = (
        UniqueConstraint("learner_id", "achievement_id", name="uq_learner_achievement"),
    )