"""Initial schema

Revision ID: eacd7fc1992f
Revises: 
Create Date: 2025-12-11 13:52:56.465579

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eacd7fc1992f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create daily_entries table
    op.create_table(
        'daily_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('date', sa.Date(), unique=True, nullable=False),
        sa.Column('eggs_collected', sa.Integer(), default=0),
        sa.Column('eggs_broken', sa.Integer(), default=0),
        sa.Column('eggs_good', sa.Integer(), default=0),
        sa.Column('eggs_sold', sa.Integer(), default=0),
        sa.Column('crates_sold', sa.Integer(), default=0),
        sa.Column('income', sa.Float(), default=0.0),
        sa.Column('feed_used_kg', sa.Float(), default=0.0),
        sa.Column('feed_cost', sa.Float(), default=0.0),
        sa.Column('mortality_count', sa.Integer(), default=0),
        sa.Column('mortality_reasons', sa.String(), default=""),
        sa.Column('flock_added', sa.Integer(), default=0),
        sa.Column('flock_removed', sa.Integer(), default=0),
        sa.Column('flock_total', sa.Integer(), default=0),
        sa.Column('notes', sa.String(), default=""),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    
    # Create settings table
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(), unique=True, nullable=False),
        sa.Column('value', sa.String(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('settings')
    op.drop_table('daily_entries')
