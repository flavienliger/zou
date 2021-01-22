"""empty message

Revision ID: e6660f1ae72c
Revises: 6c38dac574a2
Create Date: 2020-11-03 17:23:41.421979

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = 'e6660f1ae72c'
down_revision = '6c38dac574a2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('colorspace', sa.String(length=40), nullable=True))
    op.add_column('project', sa.Column('disk', sa.String(length=10), nullable=True))
    op.add_column('project', sa.Column('export_name', sa.String(length=200), nullable=True))
    op.add_column('project', sa.Column('supervisor', sa.String(length=40), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project', 'supervisor')
    op.drop_column('project', 'export_name')
    op.drop_column('project', 'disk')
    op.drop_column('project', 'colorspace')
    # ### end Alembic commands ###