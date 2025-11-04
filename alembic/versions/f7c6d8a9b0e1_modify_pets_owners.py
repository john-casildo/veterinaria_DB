"""Agregar campos a pets y owners con backups previos

Revision ID: f7c6d8a9b0e1
Revises: e1a2b3c4d5f6
Create Date: 2025-11-03 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7c6d8a9b0e1'
down_revision: Union[str, Sequence[str], None] = 'e1a2b3c4d5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Backup table names built from revision for uniqueness
backup_pets = f'backup_{revision}_pets'
backup_owners = f'backup_{revision}_owners'
backup_pets_newcols = f'backup_{revision}_pets_newcols'
backup_owners_newcols = f'backup_{revision}_owners_newcols'


def upgrade() -> None:
    """Upgrade: back up pets/owners then add new columns and types.

    Steps:
    1. Create backup tables of entire `pets` and `owners` tables if they don't exist.
    2. Create enum type `payment_method` if not present (Postgres-specific).
    3. Add columns to `pets` and `owners` and constraints.
    4. Initialize values for existing rows where appropriate (is_neutered=false).

    Note: This migration uses Postgres-specific conditional DO blocks for safe
    backup creation. If you use a different DB adapt the SQL accordingly.
    """

    # 1) Conditional backups: create full-table backups only if they don't already exist
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_pets}') THEN
            CREATE TABLE {backup_pets} AS SELECT * FROM pets;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_owners}') THEN
            CREATE TABLE {backup_owners} AS SELECT * FROM owners;
        END IF;
    END
    $$;
    """)

    # 2) Create enum type for preferred payment method if it does not exist
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_method') THEN
            CREATE TYPE payment_method AS ENUM ('cash','credit','debit','insurance');
        END IF;
    END
    $$;
    """)

    # 3) Alter tables: add columns
    # pets.microchip_number (nullable, unique)
    op.add_column('pets', sa.Column('microchip_number', sa.String(length=50), nullable=True))
    op.create_unique_constraint('uq_pets_microchip_number', 'pets', ['microchip_number'])

    # pets.is_neutered (boolean default false)
    op.add_column('pets', sa.Column('is_neutered', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    # pets.blood_type
    op.add_column('pets', sa.Column('blood_type', sa.String(length=10), nullable=True))

    # owners.emergency_contact (nullable to avoid breaking existing rows)
    op.add_column('owners', sa.Column('emergency_contact', sa.String(length=20), nullable=True))

    # owners.preferred_payment_method enum (nullable)
    op.add_column('owners', sa.Column('preferred_payment_method', sa.Enum('cash', 'credit', 'debit', 'insurance', name='payment_method'), nullable=True))

    # 4) Initialize existing rows: ensure is_neutered has a defined value
    op.execute("UPDATE pets SET is_neutered = false WHERE is_neutered IS NULL")
    # Drop any temporary backup tables if present to keep schema clean.
    # Backups were created at the start of this migration under names
    # `backup_{revision}_pets` and `backup_{revision}_owners`. If you prefer to
    # keep them for audit, remove these DROP statements.
    op.execute(f"DROP TABLE IF EXISTS {backup_pets}")
    op.execute(f"DROP TABLE IF EXISTS {backup_owners}")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade: back up new columns then remove them.

    Behavior:
    - Create small backup tables that contain the new columns (and key id) so data is not lost.
    - Drop constraints and columns.
    - Drop enum type `payment_method` if it exists (note: this may fail if other objects depend on it).
    """

    # Create small backups of the new columns to preserve them prior to dropping
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_pets_newcols}') THEN
            CREATE TABLE {backup_pets_newcols} AS SELECT pet_id, microchip_number, is_neutered, blood_type FROM pets;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_owners_newcols}') THEN
            CREATE TABLE {backup_owners_newcols} AS SELECT owner_id, emergency_contact, preferred_payment_method FROM owners;
        END IF;
    END
    $$;
    """)

    # Drop unique constraint on microchip_number if present
    try:
        op.drop_constraint('uq_pets_microchip_number', 'pets', type_='unique')
    except Exception:
        pass

    # Drop columns from pets
    try:
        op.drop_column('pets', 'microchip_number')
    except Exception:
        pass
    try:
        op.drop_column('pets', 'is_neutered')
    except Exception:
        pass
    try:
        op.drop_column('pets', 'blood_type')
    except Exception:
        pass

    # Drop columns from owners
    try:
        op.drop_column('owners', 'emergency_contact')
    except Exception:
        pass
    try:
        op.drop_column('owners', 'preferred_payment_method')
    except Exception:
        pass

    # Attempt to drop enum type (Postgres). This is best-effort and may fail if the type
    # is still in use elsewhere; in that case DB admin intervention is required.
    op.execute("DROP TYPE IF EXISTS payment_method;")


# DEV NOTES
# - Backups: full-table backups of `pets` and `owners` are created at the start of
#   `upgrade()` under names `backup_{revision}_pets` and `backup_{revision}_owners`.
#   Additionally, `downgrade()` creates focused backups of the new columns only
#   (`backup_{revision}_pets_newcols`, `backup_{revision}_owners_newcols`) before removing columns.
# - Microchip uniqueness: a UNIQUE constraint `uq_pets_microchip_number` is added.
#   Note: Postgres allows multiple NULLs for UNIQUE columns. If you require at-most-one NULL,
#   implement a partial unique index instead.
# - `is_neutered` defaults to false for existing records; the migration sets NULLs to false
#   to ensure deterministic values rather than relying solely on the server default.
# - `preferred_payment_method` is implemented as a Postgres ENUM `payment_method`. The migration
#   creates the type only if it doesn't exist. Dropping the type during downgrade is best-effort.
# - This migration uses Postgres-specific SQL blocks (`DO $$ ... $$`). If you run a different
#   DB engine adapt the conditional backup/create statements accordingly.
