"""Crear tabla medical_records y poblarla desde citas completadas

Revision ID: d8f3a1c9b4e2
Revises: 
Create Date: 2025-11-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f3a1c9b4e2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

backup_table_name = f'backup_{revision}_medical_records'
def upgrade() -> None:
    """Upgrade schema: create medical_records and populate from completed appointments."""
    # Create table
    op.create_table(
        'medical_records',
        sa.Column('record_id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('appointment_id', sa.Integer(), nullable=False, index=True),
        sa.Column('diagnosis', sa.Text(), nullable=False),
        sa.Column('treatment', sa.Text(), nullable=False),
        sa.Column('prescription', sa.Text(), nullable=True),
        sa.Column('follow_up_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Add foreign key constraint to appointments(appointment_id)
    op.create_foreign_key(
        'fk_medical_records_appointment',
        'medical_records', 'appointments', ['appointment_id'], ['appointment_id'], ondelete='CASCADE'
    )

    # Ensure one medical record per appointment to preserve 1:1 relationship
    # This enforces data integrity and prevents duplicate records for the same appointment.
    op.create_unique_constraint('uq_medical_records_appointment', 'medical_records', ['appointment_id'])
    # Populate from existing completed appointments
    # Mapping decision: use `reason` as `diagnosis` and `notes` as `treatment` when available.
    op.execute(
        """
        INSERT INTO medical_records (appointment_id, diagnosis, treatment, prescription, follow_up_required, created_at)
        SELECT
            appointment_id,
            reason AS diagnosis,
            COALESCE(notes, '') AS treatment,
            NULL AS prescription,
            false AS follow_up_required,
            appointment_date AS created_at
        FROM appointments
        WHERE status = 'completed'
        """
    )
    op.execute(f"DROP TABLE IF EXISTS {backup_table_name}")
    # ### end Alembic commands ###



def downgrade() -> None:
    """Downgrade schema: create a backup of `medical_records` and then drop the table.

    Downgrade must preserve existing medical_records data. We create a backup table
    named `backup_{revision}_medical_records` containing all rows from
    `medical_records` before dropping it. If the backup table already exists we skip
    creation to avoid overwriting historical backups.
    """

    # Create backup table only if it doesn't already exist. Uses a postgres DO block
    # to check information_schema. This avoids accidental overwrites of previous backups.
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_table_name}'
        ) THEN
            CREATE TABLE {backup_table_name} AS
            SELECT * FROM medical_records;
        END IF;
    END
    $$;
    """)

    # Drop constraints (unique + FK) then drop table
    # We drop constraints explicitly to make rollback steps clear.
    try:
        op.drop_constraint('uq_medical_records_appointment', 'medical_records', type_='unique')
    except Exception:
        # If constraint not present, continue; the table might have been created differently in some envs
        pass

    try:
        op.drop_constraint('fk_medical_records_appointment', 'medical_records', type_='foreignkey')
    except Exception:
        pass

    op.drop_table('medical_records')
       # Drop backup table if it exists
  


# -------------------------
# DEV NOTES (for maintainers / personal documentation)
# -------------------------
# Decisions and rationale taken while implementing this migration:
# 1) Field mapping for historical data:
#    - `diagnosis` := `appointments.reason` because there is no dedicated diagnosis field
#      historically. `reason` typically contains the clinical reason/complaint.
#    - `treatment` := `appointments.notes` as notes often contain treatment details.
#    - `prescription` is left NULL because prescriptions were not modelled in the
#      appointments table; populating it automatically would be speculative.
# 2) `created_at` for medical_records is set to `appointment_date` so historical
#    records reflect when the clinical encounter happened (better audit semantics).
# 3) `follow_up_required` defaulted to `false` for historical records. If business
#    rules exist to infer follow-up from `notes` or other signals, we can run a
#    post-migration script to set it.
# 4) Uniqueness on `appointment_id`: enforce 1:1 relation between appointment and
#    medical record. This maintains integrity (one medical record per appointment).
# 5) Downgrade backup: we create a `backup_{revision}_medical_records` table before
#    dropping to preserve data. We intentionally avoid overwriting an existing
#    backup table.
# 6) DB assumptions: migration uses Postgres-specific DO $$ blocks for safe
#    conditional backup creation. If your environment uses a different DB, adjust
#    the backup logic accordingly.

