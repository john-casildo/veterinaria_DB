"""Agregar métricas y optimizaciones a veterinarians y pets

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2025-11-03 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


backup_vets = f'backup_{revision}_veterinarians'
backup_pets = f'backup_{revision}_pets'
backup_vets_newcols = f'backup_{revision}_veterinarians_newcols'
backup_pets_newcols = f'backup_{revision}_pets_newcols'


def upgrade() -> None:
    """Upgrade: add metric columns and populate them from historical appointments.

    Steps:
    - Create full-table backups of `veterinarians` and `pets` (if not present).
    - Add columns to `veterinarians`: consultation_fee, rating, total_appointments.
    - Add columns to `pets`: last_visit_date, visit_count.
    - Populate total_appointments and visit_count/last_visit_date from appointments where status = 'completed'.

    Notes:
    - consultation_fee and rating cannot be reliably derived from existing schema
      (no pricing or reviews). consultation_fee defaults to 0.00, rating left NULL.
    - All backup and conditional logic uses Postgres-specific DO $$ blocks.
    """

    # 1) Full-table backups if not already created
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_vets}') THEN
            CREATE TABLE {backup_vets} AS SELECT * FROM veterinarians;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_pets}') THEN
            CREATE TABLE {backup_pets} AS SELECT * FROM pets;
        END IF;
    END
    $$;
    """)

    # 2) Add columns to veterinarians
    op.add_column('veterinarians', sa.Column('consultation_fee', sa.Numeric(8, 2), nullable=False, server_default='0.00'))
    op.add_column('veterinarians', sa.Column('rating', sa.Numeric(3, 2), nullable=True))
    op.add_column('veterinarians', sa.Column('total_appointments', sa.Integer(), nullable=False, server_default='0'))

    # 3) Add columns to pets
    op.add_column('pets', sa.Column('last_visit_date', sa.Date(), nullable=True))
    op.add_column('pets', sa.Column('visit_count', sa.Integer(), nullable=False, server_default='0'))

    # 4) Populate aggregated values from appointments (completed only)
    # total_appointments per veterinarian
    op.execute("""
    UPDATE veterinarians v
    SET total_appointments = coalesce(sub.cnt, 0)
    FROM (
        SELECT veterinarian_id, COUNT(*) AS cnt
        FROM appointments
        WHERE status = 'completed'
        GROUP BY veterinarian_id
    ) sub
    WHERE v.veterinarian_id = sub.veterinarian_id;
    """)

    # visit_count and last_visit_date per pet
    op.execute("""
    UPDATE pets p
    SET visit_count = coalesce(sub.cnt, 0), last_visit_date = sub.last_date
    FROM (
        SELECT pet_id, COUNT(*) AS cnt, MAX(appointment_date)::date AS last_date
        FROM appointments
        WHERE status = 'completed'
        GROUP BY pet_id
    ) sub
    WHERE p.pet_id = sub.pet_id;
    """)

    # Ensure default values applied where aggregates returned NULL
    op.execute("UPDATE veterinarians SET total_appointments = 0 WHERE total_appointments IS NULL")
    op.execute("UPDATE pets SET visit_count = 0 WHERE visit_count IS NULL")

    # Optionally drop the full backups to keep schema clean. Remove these DROP statements
    # if you prefer to keep the full backups for auditing.
    op.execute(f"DROP TABLE IF EXISTS {backup_vets}")
    op.execute(f"DROP TABLE IF EXISTS {backup_pets}")


def downgrade() -> None:
    """Downgrade: preserve new column values then remove them.

    Steps:
    - Create focused backups containing only the new columns and primary keys.
    - Drop added columns (best-effort) and server defaults.
    """

    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_vets_newcols}') THEN
            CREATE TABLE {backup_vets_newcols} AS SELECT veterinarian_id, consultation_fee, rating, total_appointments FROM veterinarians;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_pets_newcols}') THEN
            CREATE TABLE {backup_pets_newcols} AS SELECT pet_id, last_visit_date, visit_count FROM pets;
        END IF;
    END
    $$;
    """)

    # Drop columns (best-effort)
    try:
        op.drop_column('veterinarians', 'consultation_fee')
    except Exception:
        pass
    try:
        op.drop_column('veterinarians', 'rating')
    except Exception:
        pass
    try:
        op.drop_column('veterinarians', 'total_appointments')
    except Exception:
        pass

    try:
        op.drop_column('pets', 'last_visit_date')
    except Exception:
        pass
    try:
        op.drop_column('pets', 'visit_count')
    except Exception:
        pass


# DEV NOTES
# - `consultation_fee` and `rating` could not be derived from existing schema because
#   there are no service/pricing or review entities. consultation_fee defaults to 0.00
#   and rating is left NULL for manual or future automated population.
# - `total_appointments` and `visit_count` are computed from appointments with status='completed'.
# - `last_visit_date` is derived from the latest appointment_date for completed appointments.
# - Full-table backups are created at the start of upgrade but dropped at the end of the
#   upgrade to avoid leaving large extraneous tables; change behavior if you want to retain them.
# - All conditional backup logic uses Postgres-specific SQL.
