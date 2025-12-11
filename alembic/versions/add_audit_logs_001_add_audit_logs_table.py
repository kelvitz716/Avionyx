"""Add audit_logs table

Revision ID: add_audit_logs_001
Revises: eacd7fc1992f
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_audit_logs_001'
down_revision: Union[str, Sequence[str], None] = 'eacd7fc1992f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('details', sa.String(), default=""),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('audit_logs')
