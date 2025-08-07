"""Initial schema creation

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('preferences', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('memory_limit', sa.Integer(), nullable=False),
        sa.Column('storage_limit_mb', sa.Integer(), nullable=False),
        sa.Column('api_rate_limit', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index('idx_users_role_active', 'users', ['role', 'is_active'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create memories table
    op.create_table('memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('memory_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('importance_score', sa.Float(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('retention_strength', sa.Float(), nullable=False),
        sa.Column('retrieval_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_memories_created', 'memories', ['created_at'], unique=False)
    op.create_index('idx_memories_user_status', 'memories', ['user_id', 'status'], unique=False)
    op.create_index('idx_memories_user_type', 'memories', ['user_id', 'memory_type'], unique=False)

    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('messages', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('context', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sessions_last_activity', 'sessions', ['last_activity_at'], unique=False)
    op.create_index('idx_sessions_user_active', 'sessions', ['user_id', 'is_active'], unique=False)

    # Create tags table
    op.create_table('tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_tag_name')
    )
    op.create_index('idx_tags_user_usage', 'tags', ['user_id', 'usage_count'], unique=False)

    # Create events table
    op.create_table('events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_version', sa.Integer(), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('causation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stream_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aggregate_id', 'stream_version', name='uq_aggregate_version')
    )
    op.create_index('idx_events_type_created', 'events', ['event_type', 'created_at'], unique=False)
    op.create_index(op.f('ix_events_aggregate_id'), 'events', ['aggregate_id'], unique=False)
    op.create_index(op.f('ix_events_correlation_id'), 'events', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_events_created_at'), 'events', ['created_at'], unique=False)
    op.create_index(op.f('ix_events_event_type'), 'events', ['event_type'], unique=False)

    # Create snapshots table
    op.create_table('snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aggregate_id', 'version', name='uq_snapshot_version')
    )
    op.create_index(op.f('ix_snapshots_aggregate_id'), 'snapshots', ['aggregate_id'], unique=False)

    # Create memory_links table
    op.create_table('memory_links',
        sa.Column('from_memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('link_type', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['from_memory_id'], ['memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_memory_id'], ['memories.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('from_memory_id', 'to_memory_id', name='uq_memory_links')
    )

    # Create memory_tags table
    op.create_table('memory_tags',
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('memory_id', 'tag_id', name='uq_memory_tags')
    )

    # Create session_memories table
    op.create_table('session_memories',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['memory_id'], ['memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_id', 'memory_id', name='uq_session_memories')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('session_memories')
    op.drop_table('memory_tags')
    op.drop_table('memory_links')
    op.drop_table('snapshots')
    op.drop_table('events')
    op.drop_table('tags')
    op.drop_table('sessions')
    op.drop_table('memories')
    op.drop_table('users')
