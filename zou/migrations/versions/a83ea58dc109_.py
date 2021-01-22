"""empty message

Revision ID: a83ea58dc109
Revises: b2d6e9da4b91
Create Date: 2020-07-16 11:50:46.276083

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = 'a83ea58dc109'
down_revision = 'b2d6e9da4b91'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('children_file', sa.Column('path', sa.String(length=400), nullable=True))
    op.create_unique_constraint(None, 'children_file', ['path'])
    op.drop_column('output_file', 'frame_end')
    op.drop_column('output_file', 'frame_start')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('output_file', sa.Column('frame_start', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('output_file', sa.Column('frame_end', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'children_file', type_='unique')
    op.drop_column('children_file', 'path')
    # ### end Alembic commands ###