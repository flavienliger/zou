"""empty message

Revision ID: 37c36148388f
Revises: 2cfe26d7bc27
Create Date: 2020-08-13 10:38:02.492886

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '37c36148388f'
down_revision = '2cfe26d7bc27'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('children_file', sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('children_file', 'data')
    # ### end Alembic commands ###