"""empty message

Revision ID: 2cfe26d7bc27
Revises: a83ea58dc109
Create Date: 2020-07-16 16:15:21.724433

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = '2cfe26d7bc27'
down_revision = 'a83ea58dc109'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('children_file', sa.Column('render_info', sa.String(length=200), nullable=True))
    op.add_column('output_file', sa.Column('render_info', sa.String(length=200), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('output_file', 'render_info')
    op.drop_column('children_file', 'render_info')
    # ### end Alembic commands ###
