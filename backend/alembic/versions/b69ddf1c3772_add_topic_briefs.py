"""add_topic_briefs

Revision ID: b69ddf1c3772
Revises: 3b9f3c4a7f2b
Create Date: 2026-01-09 20:44:19.357876

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b69ddf1c3772'
down_revision = '3b9f3c4a7f2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create topic_briefs table
    op.create_table(
        'topic_briefs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brief_id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('summary_short', sa.Text(), nullable=False),
        sa.Column('summary_full', sa.Text(), nullable=False),
        sa.Column('content_item_ids', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('content_references', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_provider', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('prompt_version', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['brief_id'], ['briefs.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_topic_briefs_brief_id'), 'topic_briefs', ['brief_id'], unique=False)
    op.create_index(op.f('ix_topic_briefs_id'), 'topic_briefs', ['id'], unique=False)
    op.create_index(op.f('ix_topic_briefs_topic_id'), 'topic_briefs', ['topic_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_topic_briefs_topic_id'), table_name='topic_briefs')
    op.drop_index(op.f('ix_topic_briefs_id'), table_name='topic_briefs')
    op.drop_index(op.f('ix_topic_briefs_brief_id'), table_name='topic_briefs')

    # Drop table
    op.drop_table('topic_briefs')
