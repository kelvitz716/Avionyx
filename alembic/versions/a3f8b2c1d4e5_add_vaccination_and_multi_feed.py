"""add vaccination and multi-feed tracking

Revision ID: a3f8b2c1d4e5
Revises: 21a192c0f215
Create Date: 2024-12-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8b2c1d4e5'
down_revision: Union[str, None] = '21a192c0f215'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to inventory_items
    op.add_column('inventory_items', sa.Column('expiry_date', sa.Date(), nullable=True))
    op.add_column('inventory_items', sa.Column('bag_weight', sa.Float(), nullable=True))
    
    # Add current_count column to flocks
    op.add_column('flocks', sa.Column('current_count', sa.Integer(), server_default='0', nullable=True))
    
    # Create vaccination_records table
    op.create_table(
        'vaccination_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('flock_id', sa.Integer(), sa.ForeignKey('flocks.id'), nullable=False),
        sa.Column('vaccine_name', sa.String(), nullable=False),
        sa.Column('doses_used', sa.Integer(), nullable=False),
        sa.Column('birds_vaccinated', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('next_due_date', sa.Date(), nullable=True),
        sa.Column('vaccinator', sa.String(), server_default='Self', nullable=True),
        sa.Column('notes', sa.String(), server_default='', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    
    # Create daily_feed_usage table
    op.create_table(
        'daily_feed_usage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('daily_entry_id', sa.Integer(), sa.ForeignKey('daily_entries.id'), nullable=False),
        sa.Column('feed_item_id', sa.Integer(), sa.ForeignKey('inventory_items.id'), nullable=False),
        sa.Column('quantity_kg', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # Drop new tables
    op.drop_table('daily_feed_usage')
    op.drop_table('vaccination_records')
    
    # Remove new columns
    op.drop_column('flocks', 'current_count')
    op.drop_column('inventory_items', 'bag_weight')
    op.drop_column('inventory_items', 'expiry_date')
