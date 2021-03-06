"""empty message

Revision ID: 0f5470dce98f
Revises: e6660f1ae72c
Create Date: 2020-11-03 18:16:46.358713

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '0f5470dce98f'
down_revision = 'e6660f1ae72c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project', 'disk')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('disk', sa.VARCHAR(length=10), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
