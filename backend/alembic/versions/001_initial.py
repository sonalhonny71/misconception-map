"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # learners
    op.create_table(
        'learners',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index('ix_learners_token_hash', 'learners', ['token_hash'], unique=True)

    # sessions
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('phase', sa.String(32), nullable=False, server_default='diagnostic'),
        sa.Column('step_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(32), nullable=False, server_default='in_progress'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['learner_id'], ['learners.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sessions_learner_id', 'sessions', ['learner_id'])

    # items
    op.create_table(
        'items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', sa.String(64), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('skill', sa.String(64), nullable=False),
        sa.Column('kind', sa.String(32), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('options', sa.Text(), nullable=False),
        sa.Column('correct_option_id', sa.String(64), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('discriminates', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id'),
    )
    op.create_index('ix_items_item_id', 'items', ['item_id'], unique=True)
    op.create_index('ix_items_level_kind', 'items', ['level', 'kind'])

    # served_items
    op.create_table(
        'served_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('option_order', sa.Text(), nullable=False),
        sa.Column('served_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_served_items_session_id', 'served_items', ['session_id'])

    # responses
    op.create_table(
        'responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('served_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chosen_option_id', sa.String(64), nullable=True),
        sa.Column('is_correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('misconception_id', sa.String(64), nullable=True),
        sa.Column('kind', sa.String(32), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['learner_id'], ['learners.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['served_item_id'], ['served_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'served_item_id', name='uq_session_served_item'),
    )
    op.create_index('ix_responses_learner_id', 'responses', ['learner_id'])
    op.create_index('ix_responses_session_id', 'responses', ['session_id'])
    op.create_index('ix_responses_learner_kind', 'responses', ['learner_id', 'kind'])

    # hypotheses
    op.create_table(
        'hypotheses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill', sa.String(64), nullable=False),
        sa.Column('misconception_id', sa.String(64), nullable=False),
        sa.Column('evidence_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(32), nullable=False, server_default='insufficient'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['learner_id'], ['learners.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('learner_id', 'skill', 'misconception_id', name='uq_learner_skill_misconception'),
    )
    op.create_index('ix_hypotheses_learner_id', 'hypotheses', ['learner_id'])
    op.create_index('ix_hypotheses_skill_misconception', 'hypotheses', ['skill', 'misconception_id'])

    # progress
    op.create_table(
        'progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill', sa.String(64), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='not_assessed'),
        sa.Column('last_retest_score', sa.Integer(), nullable=True),
        sa.Column('last_retest_total', sa.Integer(), nullable=True),
        sa.Column('retest_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['learner_id'], ['learners.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('learner_id', 'skill', name='uq_learner_skill'),
    )
    op.create_index('ix_progress_learner_id', 'progress', ['learner_id'])

    # xp_events
    op.create_table(
        'xp_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(32), nullable=False),
        sa.Column('event_key', sa.String(128), nullable=False),
        sa.Column('xp_amount', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['learner_id'], ['learners.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_key'),
    )
    op.create_index('ix_xp_events_learner_id', 'xp_events', ['learner_id'])

    # achievements
    op.create_table(
        'achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('achievement_id', sa.String(64), nullable=False),
        sa.Column('earned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['learner_id'], ['learners.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('learner_id', 'achievement_id', name='uq_learner_achievement'),
    )
    op.create_index('ix_achievements_learner_id', 'achievements', ['learner_id'])


def downgrade() -> None:
    op.drop_table('achievements')
    op.drop_table('xp_events')
    op.drop_table('progress')
    op.drop_table('hypotheses')
    op.drop_table('responses')
    op.drop_table('served_items')
    op.drop_table('items')
    op.drop_table('sessions')
    op.drop_table('learners')