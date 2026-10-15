from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum


class SessionPhase(str, Enum):
    DIAGNOSTIC = "diagnostic"
    FOLLOWUP = "followup"
    CHECK_UNDERSTANDING = "check_understanding"
    PRACTICE = "practice"
    RETEST = "retest"
    RESULTS = "results"
    COMPLETED = "completed"


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ResponseKind(str, Enum):
    DIAGNOSTIC = "diagnostic"
    FOLLOWUP = "followup"
    CHECK = "check"
    PRACTICE = "practice"
    RETEST = "retest"


class HypothesisStatus(str, Enum):
    INSUFFICIENT = "insufficient"
    POSSIBLE = "possible"
    SUPPORTED = "supported"


class SkillStatus(str, Enum):
    NOT_ASSESSED = "not_assessed"
    EVIDENCE_OF_DIFFICULTY = "evidence_of_difficulty"
    PRACTICING = "practicing"
    ENCOURAGING_EVIDENCE = "encouraging_evidence"
    CONSISTENT_EVIDENCE = "consistent_evidence"
    NEEDS_MORE_PRACTICE = "needs_more_practice"


class LearnerCreate(BaseModel):
    pass  # No input needed, token generated server-side


class LearnerOut(BaseModel):
    token: str
    token_hash: str

    class Config:
        from_attributes = True


class HealthOut(BaseModel):
    status: str
    database: str
    timestamp: datetime


class LevelSummary(BaseModel):
    id: int
    name: str
    title: str
    description: str
    status: SkillStatus
    progress_percent: int
    last_retest_score: Optional[int] = None
    last_retest_total: Optional[int] = None


class LevelsOut(BaseModel):
    levels: List[LevelSummary]


class SessionCreate(BaseModel):
    level: int = Field(ge=1, le=5)


class SessionOut(BaseModel):
    id: UUID
    level: int
    phase: SessionPhase
    step_index: int
    status: SessionStatus
    started_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OptionOut(BaseModel):
    id: str
    text: str


class QuestionOut(BaseModel):
    served_item_id: UUID
    item_id: str  # logical item ID
    prompt: str  # LaTeX
    options: List[OptionOut]
    step_label: str
    phase: SessionPhase
    step_index: int
    total_steps: int


class AnswerIn(BaseModel):
    served_item_id: UUID
    option_id: Optional[str] = None  # null means "unsure"


class FeedbackOut(BaseModel):
    is_correct: bool
    explanation: str  # LaTeX
    step_note: Optional[str] = None  # LaTeX
    misconception_id: Optional[str] = None
    next_phase: SessionPhase
    next_step_label: str
    xp_awarded: int = 0


class AnswerOut(BaseModel):
    feedback: FeedbackOut
    next_question: Optional[QuestionOut] = None
    session: SessionOut


class InsightHypothesis(BaseModel):
    skill: str
    misconception_id: str
    misconception_label: str
    status: HypothesisStatus
    evidence_score: float
    evidence_trail: List[Dict[str, Any]]


class InsightsOut(BaseModel):
    hypotheses: List[InsightHypothesis]
    recent_evidence: List[Dict[str, Any]]


class ProgressSkill(BaseModel):
    skill: str
    level: int
    status: SkillStatus
    last_retest_score: Optional[int] = None
    last_retest_total: Optional[int] = None
    retest_count: int


class ProgressOut(BaseModel):
    total_xp: int
    practice_sets_completed: int
    latest_retest: Optional[Dict[str, Any]] = None
    skills: List[ProgressSkill]
    achievements: List[str]
    history: List[Dict[str, Any]]


class MisconceptionMapNode(BaseModel):
    skill: str
    level: int
    status: SkillStatus
    evidence_count: int
    attempts: int
    last_retest_score: Optional[int] = None
    last_retest_total: Optional[int] = None
    dependencies: List[str] = []


class MisconceptionMapOut(BaseModel):
    nodes: List[MisconceptionMapNode]


class ErrorOut(BaseModel):
    code: str
    message: str