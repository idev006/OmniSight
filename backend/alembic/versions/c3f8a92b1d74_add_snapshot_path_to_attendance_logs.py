"""add snapshot_path to attendance_logs

Revision ID: c3f8a92b1d74
Revises: 5c8af185b9ff
Create Date: 2026-05-18 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3f8a92b1d74'
down_revision: Union[str, None] = '5c8af185b9ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'attendance_logs',
        sa.Column('snapshot_path', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('attendance_logs', 'snapshot_path')
