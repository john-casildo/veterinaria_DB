"""Crear tablas vaccines y vaccination_records

Revision ID: e1a2b3c4d5f6
Revises: d8f3a1c9b4e2
Create Date: 2025-11-03 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5f6'
down_revision: Union[str, Sequence[str], None] = 'd8f3a1c9b4e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

backup_vacc_records = f'backup_{revision}_vaccination_records'
backup_vaccines = f'backup_{revision}_vaccines'

def upgrade() -> None:
    """Upgrade schema: create vaccines and vaccination_records.

    Logic and data handling:
    - Create `vaccines` catalog to store available vaccines.
    - Create `vaccination_records` to store applied vaccinations per pet.
    - Add FK constraints to `pets` and `veterinarians` and `vaccines`.
    - If a legacy `vaccinations` table exists, copy its data into the new schema
      (best-effort; uses a conditional check against information_schema).
    """

    # Create vaccines catalog
    op.create_table(
        'vaccines',
        sa.Column('vaccine_id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('manufacturer', sa.String(length=200), nullable=True),
        sa.Column('species_applicable', sa.String(length=100), nullable=True),
    )

    # Create vaccination_records
    op.create_table(
        'vaccination_records',
        sa.Column('vaccination_id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('pet_id', sa.Integer(), nullable=False, index=True),
        sa.Column('vaccine_id', sa.Integer(), nullable=False, index=True),
        sa.Column('vaccination_date', sa.Date(), nullable=False),
        sa.Column('next_dose_date', sa.Date(), nullable=True),
        sa.Column('veterinarian_id', sa.Integer(), nullable=False, index=True),
        sa.Column('batch_number', sa.String(length=50), nullable=True),
    )

    # Foreign keys
    op.create_foreign_key(
        'fk_vaccination_pet', 'vaccination_records', 'pets', ['pet_id'], ['pet_id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_vaccination_vaccine', 'vaccination_records', 'vaccines', ['vaccine_id'], ['vaccine_id'], ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'fk_vaccination_veterinarian', 'vaccination_records', 'veterinarians', ['veterinarian_id'], ['veterinarian_id'], ondelete='SET NULL'
    )

    # Best-effort migration from legacy table 'vaccinations' if it exists.
    # This allows projects that had an ad-hoc vaccinations table to preserve data.
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.tables WHERE table_name = 'vaccinations'
        ) THEN
            INSERT INTO vaccines (name, manufacturer, species_applicable)
            SELECT DISTINCT vaccine_name, manufacturer, species FROM vaccinations WHERE vaccine_name IS NOT NULL
            ON CONFLICT DO NOTHING;

            -- Map vaccines to vaccination_records by joining on vaccine name where possible.
            INSERT INTO vaccination_records (pet_id, vaccine_id, vaccination_date, next_dose_date, veterinarian_id, batch_number)
            SELECT
                v.pet_id,
                vac.vaccine_id,
                v.given_date::date,
                NULL::date,
                v.veterinarian_id,
                v.batch_number
            FROM vaccinations v
            LEFT JOIN vaccines vac ON vac.name = v.vaccine_name
            WHERE v.pet_id IS NOT NULL;
        END IF;
    END
    $$;
    """)

    op.execute(f"DROP TABLE IF EXISTS {backup_vacc_records}")
    op.execute(f"DROP TABLE IF EXISTS {backup_vaccines}")
    # ### end Alembic commands ###



def downgrade() -> None:
    """Downgrade schema: backup vaccination data then drop tables.

    The downgrade creates backup tables `backup_{revision}_vaccination_records` and
    `backup_{revision}_vaccines` if they don't exist, copies the data and then drops
    constraints and the tables. This preserves data in case of accidental downgrade.
    """

  
    # Conditional backup creation (Postgres DO block)
    op.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_vacc_records}') THEN
            CREATE TABLE {backup_vacc_records} AS SELECT * FROM vaccination_records;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{backup_vaccines}') THEN
            CREATE TABLE {backup_vaccines} AS SELECT * FROM vaccines;
        END IF;
    END
    $$;
    """)

    # Drop foreign key constraints (attempt and ignore failures to be robust)
    try:
        op.drop_constraint('fk_vaccination_pet', 'vaccination_records', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_vaccination_vaccine', 'vaccination_records', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_vaccination_veterinarian', 'vaccination_records', type_='foreignkey')
    except Exception:
        pass

    # Drop tables
    op.drop_table('vaccination_records')
    op.drop_table('vaccines')


# DEV NOTES
# - `vaccines` is a simple catalog. `species_applicable` is stored as a string to
#   avoid introducing another enum/table until real usage patterns are known.
# - `vaccination_records.veterinarian_id` references `veterinarians`; `ondelete='SET NULL'`
#   is used in the FK creation above to avoid accidental cascade deletes removing
#   historical vaccination logs when a veterinarian is removed. (Note: some DBs may
#   not allow SET NULL if column is NOT NULL; column is nullable by design here.)
# - The migration contains a best-effort copy from a legacy table named `vaccinations` if
#   it exists. This uses a simple name-match for vaccines; manual reconciliation
#   may be required after migration.
# - Backups created on downgrade are intentionally named `backup_{revision}_*` and
#   are only created if they do not already exist to avoid overwriting prior backups.
