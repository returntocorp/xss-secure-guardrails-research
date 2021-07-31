"""Add 'not_relevant' to triage_status; add new field 'taxonomy' to Findings

Revision ID: 5ae427c7ad96
Revises: 
Create Date: 2021-01-11 16:56:11.064629

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5ae427c7ad96'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('finding', sa.Column('taxonomy', sa.Enum('A', 'B', 'C', 'D', 'E', name='taxonomy'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('finding', 'taxonomy')
    # ### end Alembic commands ###
