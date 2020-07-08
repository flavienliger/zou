"""empty message

Revision ID: 72dd6c38dbf0
Revises: e225f551ff45
Create Date: 2020-07-03 13:41:44.233554

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql
import sqlalchemy_utils
import uuid

# revision identifiers, used by Alembic.
revision = '72dd6c38dbf0'
down_revision = 'e225f551ff45'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dependent', sa.Column('a', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False))
    op.add_column('dependent', sa.Column('b', sqlalchemy_utils.types.uuid.UUIDType(binary=False), default=uuid.uuid4, nullable=False))
    op.drop_constraint('dependent_output_file_fkey', 'dependent', type_='foreignkey')
    op.drop_constraint('dependent_dependent_file_fkey', 'dependent', type_='foreignkey')
    op.create_foreign_key(None, 'dependent', 'output_file', ['a'], ['id'])
    op.create_foreign_key(None, 'dependent', 'dependent_file', ['b'], ['id'])
    op.drop_column('dependent', 'output_file')
    op.drop_column('dependent', 'dependent_file')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('dependent', sa.Column('dependent_file', postgresql.UUID(), autoincrement=False, nullable=True))
    op.add_column('dependent', sa.Column('output_file', postgresql.UUID(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'dependent', type_='foreignkey')
    op.drop_constraint(None, 'dependent', type_='foreignkey')
    op.create_foreign_key('dependent_dependent_file_fkey', 'dependent', 'dependent_file', ['dependent_file'], ['id'])
    op.create_foreign_key('dependent_output_file_fkey', 'dependent', 'output_file', ['output_file'], ['id'])
    op.drop_column('dependent', 'b')
    op.drop_column('dependent', 'a')
    # ### end Alembic commands ###
