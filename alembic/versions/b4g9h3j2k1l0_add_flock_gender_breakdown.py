"""Add hens_count and roosters_count to flocks

Revision ID: b4g9h3j2k1l0
Revises: a3f8b2c1d4e5
Create Date: 2025-12-18 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4g9h3j2k1l0'
down_revision = 'a3f8b2c1d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('flocks', sa.Column('hens_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('flocks', sa.Column('roosters_count', sa.Integer(), server_default='0', nullable=True))


def downgrade() -> None:
    op.drop_column('flocks', 'roosters_count')
    op.drop_column('flocks', 'hens_count')
