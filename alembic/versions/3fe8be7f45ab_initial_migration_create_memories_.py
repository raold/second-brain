"""Initial migration - create memories, search_history, and user_feedback tables

Revision ID: 3fe8be7f45ab
Revises: 
Create Date: 2025-07-16 16:38:30.326290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3fe8be7f45ab'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create memories table
    op.create_table(
        'memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('embedding_vector', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('intent_type', sa.String(length=50), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('embedding_dimensions', sa.Integer(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=True, default='normal'),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('memory_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True, default=1),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('feedback_score', sa.Float(), nullable=True, default=0.0),
        sa.Column('access_count', sa.Integer(), nullable=True, default=0),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create search_history table
    op.create_table(
        'search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result_count', sa.Integer(), nullable=True),
        sa.Column('clicked_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('search_type', sa.String(length=50), nullable=True),
        sa.Column('filters_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('user_satisfaction', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_feedback table
    op.create_table(
        'user_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_type', sa.String(length=50), nullable=False),
        sa.Column('feedback_value', sa.Text(), nullable=True),
        sa.Column('feedback_score', sa.Float(), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('ix_memories_created_at', 'memories', ['created_at'])
    op.create_index('ix_memories_intent_type', 'memories', ['intent_type'])
    op.create_index('ix_memories_is_active', 'memories', ['is_active'])
    op.create_index('ix_memories_parent_id', 'memories', ['parent_id'])
    op.create_index('ix_memories_priority', 'memories', ['priority'])
    op.create_index('ix_memories_source', 'memories', ['source'])
    op.create_index('ix_search_history_created_at', 'search_history', ['created_at'])
    op.create_index('ix_user_feedback_memory_id', 'user_feedback', ['memory_id'])
    op.create_index('ix_user_feedback_feedback_type', 'user_feedback', ['feedback_type'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_user_feedback_feedback_type')
    op.drop_index('ix_user_feedback_memory_id')
    op.drop_index('ix_search_history_created_at')
    op.drop_index('ix_memories_source')
    op.drop_index('ix_memories_priority')
    op.drop_index('ix_memories_parent_id')
    op.drop_index('ix_memories_is_active')
    op.drop_index('ix_memories_intent_type')
    op.drop_index('ix_memories_created_at')
    
    # Drop tables
    op.drop_table('user_feedback')
    op.drop_table('search_history')
    op.drop_table('memories')
