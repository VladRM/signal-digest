"""Connector/endpoints refactor with Tavily queries.

Revision ID: 4f2b0a6f3d8a
Revises: b69ddf1c3772
Create Date: 2026-01-10 10:12:00.000000
"""
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "4f2b0a6f3d8a"
down_revision = "b69ddf1c3772"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename enum type and add Tavily connector.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sourcetype')
               AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connectortype')
            THEN
                ALTER TYPE sourcetype RENAME TO connectortype;
            END IF;
        END $$;
        """
    )
    with context.get_context().autocommit_block():
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connectortype')
                   AND NOT EXISTS (
                       SELECT 1
                       FROM pg_enum e
                       JOIN pg_type t ON t.oid = e.enumtypid
                       WHERE t.typname = 'connectortype'
                         AND e.enumlabel = 'TAVILY'
                   )
                THEN
                    ALTER TYPE connectortype ADD VALUE 'TAVILY';
                END IF;
            END $$;
            """
        )
    connector_enum = postgresql.ENUM(
        "RSS",
        "YOUTUBE_CHANNEL",
        "X_USER",
        "TAVILY",
        name="connectortype",
        create_type=False,
    )

    # Rename sources -> endpoints and update columns.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'sources'
            ) AND NOT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'endpoints'
            )
            THEN
                ALTER TABLE sources RENAME TO endpoints;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER INDEX IF EXISTS ix_sources_id RENAME TO ix_endpoints_id")
    op.alter_column(
        "endpoints",
        "type",
        new_column_name="connector_type",
        existing_type=sa.Enum(name="connectortype"),
    )
    op.alter_column(
        "endpoints",
        "identifier",
        new_column_name="target",
        existing_type=sa.Text(),
    )
    op.execute(
        """
        UPDATE endpoints
        SET connector_type = 'TAVILY', enabled = TRUE
        WHERE target = 'tavily:search'
        """
    )

    # Update content_items to reference endpoints and connector queries.
    op.drop_constraint(
        "content_items_source_id_fkey",
        "content_items",
        type_="foreignkey",
    )
    op.alter_column(
        "content_items",
        "source_id",
        new_column_name="endpoint_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        None, "content_items", "endpoints", ["endpoint_id"], ["id"]
    )
    op.add_column(
        "content_items",
        sa.Column("connector_query_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "content_items",
        sa.Column("connector_type", connector_enum, nullable=True),
    )

    # Backfill connector_type from endpoints.
    op.execute(
        """
        UPDATE content_items ci
        SET connector_type = e.connector_type
        FROM endpoints e
        WHERE ci.endpoint_id = e.id
        """
    )
    op.alter_column("content_items", "connector_type", nullable=False)

    op.create_table(
        "connector_queries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("connector_type", connector_enum, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "options_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_connector_queries_id"),
        "connector_queries",
        ["id"],
        unique=False,
    )
    op.create_foreign_key(
        None,
        "content_items",
        "connector_queries",
        ["connector_query_id"],
        ["id"],
    )
    op.create_check_constraint(
        "content_items_endpoint_or_query_check",
        "content_items",
        "(endpoint_id IS NULL) <> (connector_query_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "content_items_endpoint_or_query_check",
        "content_items",
        type_="check",
    )
    op.drop_constraint(
        "content_items_connector_query_id_fkey",
        "content_items",
        type_="foreignkey",
    )
    op.drop_column("content_items", "connector_query_id")
    op.drop_column("content_items", "connector_type")
    op.drop_index(op.f("ix_connector_queries_id"), table_name="connector_queries")
    op.drop_table("connector_queries")

    op.drop_constraint(
        "content_items_endpoint_id_fkey",
        "content_items",
        type_="foreignkey",
    )
    op.alter_column(
        "content_items",
        "endpoint_id",
        new_column_name="source_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        None, "content_items", "sources", ["source_id"], ["id"]
    )

    op.alter_column(
        "endpoints",
        "connector_type",
        new_column_name="type",
        existing_type=sa.Enum(name="connectortype"),
    )
    op.alter_column(
        "endpoints",
        "target",
        new_column_name="identifier",
        existing_type=sa.Text(),
    )
    op.execute("ALTER INDEX IF EXISTS ix_endpoints_id RENAME TO ix_sources_id")
    op.rename_table("endpoints", "sources")
    op.execute(
        """
        UPDATE sources
        SET type = 'RSS'
        WHERE identifier = 'tavily:search'
        """
    )

    op.execute("ALTER TYPE connectortype RENAME TO sourcetype")
