"""Crear tabla invoices y generar facturas retroactivas

Revision ID: a9b8c7d6e5f4
Revises: f7c6d8a9b0e1
Create Date: 2025-11-03 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = 'f7c6d8a9b0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


backup_invoices = f'backup_{revision}_invoices'


def upgrade() -> None:
    """Upgrade: create invoices table and generate retroactive invoices for completed appointments.

    Notes on data generation:
    - No pricing data is available in the schema; this migration creates
      placeholder invoices with monetary fields set to 0.00. Business rules
      for calculating subtotal/tax/total should be applied in a follow-up.
    - Invoice numbers are generated deterministically as `INV-{appointment_id}-{YYYYMMDD}`
      based on the appointment date to ensure reproducibility.
    - A UNIQUE constraint on `invoice_number` is added. We also enforce a
      1:1 relation between appointment and invoice with a unique constraint on
      `appointment_id` to avoid duplicate invoices for the same appointment.
    """

    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('invoice_id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('appointment_id', sa.Integer(), nullable=False, index=True),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('payment_status', sa.Enum('pending', 'partial', 'paid', 'overdue', name='payment_status'), nullable=False, server_default='pending'),
        sa.Column('payment_date', sa.DateTime(), nullable=True),
    )

    # Foreign key to appointments
    op.create_foreign_key('fk_invoices_appointment', 'invoices', 'appointments', ['appointment_id'], ['appointment_id'], ondelete='CASCADE')

    # Uniqueness constraints
    op.create_unique_constraint('uq_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_unique_constraint('uq_invoices_appointment', 'invoices', ['appointment_id'])

    # Generate invoices retroactively for completed appointments
    # - invoice_number format: INV-{appointment_id}-{YYYYMMDD}
    # - subtotal/tax/total set to 0.00 (placeholder)
    # - payment_status set to 'pending'
    op.execute("""
    INSERT INTO invoices (appointment_id, invoice_number, issue_date, subtotal, tax_amount, total_amount, payment_status, payment_date)
    SELECT
        a.appointment_id,
        'INV-' || a.appointment_id || '-' || to_char(a.appointment_date, 'YYYYMMDD') AS invoice_number,
        a.appointment_date::date AS issue_date,
        0.00::numeric AS subtotal,
        0.00::numeric AS tax_amount,
        0.00::numeric AS total_amount,
        'pending'::text AS payment_status,
        NULL::timestamp AS payment_date
    FROM appointments a
    WHERE a.status = 'completed'
      AND NOT EXISTS (SELECT 1 FROM invoices i WHERE i.appointment_id = a.appointment_id)
    """)

    # Drop any temporary backup table if present (keep schema clean). If you prefer
    # to retain backups remove these DROPs.
    op.execute(f"DROP TABLE IF EXISTS {backup_invoices}")


def downgrade() -> None:
    """Downgrade: backup invoices table then drop it and associated enum.

    - Create `backup_{revision}_invoices` (full copy) if it doesn't exist.
    - Drop constraints and table.
    - Drop enum `payment_status` (best-effort).
    """

    # Backup invoices if present
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_invoices}') THEN
            CREATE TABLE {backup_invoices} AS SELECT * FROM invoices;
        END IF;
    END
    $$;
    """)

    # Drop constraints and table
    try:
        op.drop_constraint('uq_invoices_invoice_number', 'invoices', type_='unique')
    except Exception:
        pass
    try:
        op.drop_constraint('uq_invoices_appointment', 'invoices', type_='unique')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_invoices_appointment', 'invoices', type_='foreignkey')
    except Exception:
        pass

    op.drop_table('invoices')

    # Drop enum type (Postgres) - best-effort
    op.execute("DROP TYPE IF EXISTS payment_status;")


# DEV NOTES
# - Retroactive invoices are placeholders: subtotal/tax/total are 0.00 because
#   there is no pricing or service line-items table in the current schema.
#   A follow-up migration/script should compute real amounts, create invoice lines
#   and update totals and payment status accordingly.
# - Invoice numbers are deterministic and derived from appointment id + date to
#   make the migration idempotent and reproducible. If you require a different
#   format or a global sequence, adjust the generation logic accordingly.
# - We added a UNIQUE constraint on `appointment_id` to enforce at-most-one
#   invoice per appointment. Change to allow multiple invoices per appointment
#   (for partial payments or credit notes) if needed.
# - All backup creation uses Postgres DO blocks; adapt if your DB engine differs.
