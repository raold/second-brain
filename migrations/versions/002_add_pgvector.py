"""Add pgvector extension and vector columns

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Add vector column to memories table
    op.add_column('memories', sa.Column('embedding_vector', Vector(1536), nullable=True))
    
    # Create index for vector similarity search
    op.execute('CREATE INDEX idx_memories_embedding_vector ON memories USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100)')
    
    # Add column for attachments if not exists
    op.add_column('memories', sa.Column('attachments', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    # Remove vector index
    op.execute('DROP INDEX IF EXISTS idx_memories_embedding_vector')
    
    # Remove vector column
    op.drop_column('memories', 'embedding_vector')
    
    # Remove attachments column
    op.drop_column('memories', 'attachments')
    
    # Disable pgvector extension (optional, as other apps might use it)
    # op.execute('DROP EXTENSION IF EXISTS vector')