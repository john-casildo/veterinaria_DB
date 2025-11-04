import argparse
from datetime import datetime, timedelta
import random
from decimal import Decimal

from database import SessionLocal, engine
import models
from seed import get_or_create_vet, get_or_create_owner, get_or_create_pet, get_or_create_appointment
import sys


def preflight_check(db):
    """Run quick DB checks and report existing row counts for key tables.

    Returns a dict with counts or raises an informative error on failure.
    """
    try:
        vets_count = db.query(models.Veterinarians).count()
        owners_count = db.query(models.Owners).count()
        pets_count = db.query(models.Pets).count()
        appts_count = db.query(models.Appointments).count()
    except Exception as e:
        raise RuntimeError(f"DB preflight failed: {e}") from e

    counts = {
        'veterinarians': vets_count,
        'owners': owners_count,
        'pets': pets_count,
        'appointments': appts_count,
    }
    print("Preflight counts:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    if any(v > 0 for v in counts.values()):
        print("Warning: database already contains data. Re-running seed may create duplicates but the script uses get_or_create helpers to avoid exact duplicates based on keys.")
    return counts


def seed_after(migration: int = 0):
    """Seed additional data after migrations. If migration >=5, also populate metrics (ratings/fees)."""
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # smaller batch of data
        vets = []
        for i in range(1, 3):
            vdata = dict(
                license_number=f"VET-M{migration}-{i}",
                first_name=f"Post{i}",
                last_name="Migration",
                email=f"post_mig{migration}_vet{i}@example.com",
                specialization=random.choice(["General", "Surgery", "Dentistry"]),
            )
            vets.append(get_or_create_vet(db, vdata))

        owners = []
        for i in range(1, 6):
            odata = dict(
                first_name=f"PostOwner{i}",
                last_name="Migration",
                email=f"post_mig{migration}_owner{i}@example.com",
                phone=f"+1-555-30{i:03d}",
                address=f"Post Migration St {i}",
            )
            owners.append(get_or_create_owner(db, odata))

        pets = []
        species = ["dog", "cat", "bird", "rabbit", "other"]
        for i in range(1, 11):
            owner = random.choice(owners)
            birth_dt = (datetime.utcnow() - timedelta(days=random.randint(365, 3000))).date()
            pdata = dict(
                name=f"PostPet{migration}-{i}",
                species=random.choice(species),
                breed="Mixed",
                birth_date=birth_dt,
                weight=Decimal(f"{random.uniform(1.0, 40.0):.2f}"),
                owner_id=owner.owner_id,
            )
            pets.append(get_or_create_pet(db, pdata))

        appointments = []
        now = datetime.utcnow()
        for i in range(20):
            pet = random.choice(pets)
            vet = random.choice(vets)
            offset_days = random.randint(-60, 30)
            offset_minutes = random.choice([0, 15, 30, 45])
            appt_dt = now + timedelta(days=offset_days, minutes=offset_minutes)
            status = "scheduled" if appt_dt > now else random.choices(["completed", "cancelled", "no_show"], weights=[0.8, 0.15, 0.05])[0]
            adata = dict(
                pet_id=pet.pet_id,
                veterinarian_id=vet.veterinarian_id,
                appointment_date=appt_dt,
                reason=random.choice(["Checkup", "Vaccination", "Illness", "Grooming"]),
                status=status,
                notes=f"Post-migration {migration} seeded appointment",
            )
            appointments.append(get_or_create_appointment(db, adata))

        db.commit()

        # If migration 5 or newer, populate metrics similar to migration 0005
        if migration >= 5:
            conn = db.connection()
            # total_appointments
            conn.execute(
                "UPDATE veterinarians v SET total_appointments = sub.cnt FROM (SELECT veterinarian_id, COUNT(*) AS cnt FROM appointments WHERE status = 'completed' GROUP BY veterinarian_id) sub WHERE v.veterinarian_id = sub.veterinarian_id"
            )
            # consultation_fee
            conn.execute(
                "UPDATE veterinarians v SET consultation_fee = COALESCE(sub.avg_total, 0.00)::numeric(8,2) FROM (SELECT a.veterinarian_id, AVG(i.total_amount) AS avg_total FROM appointments a JOIN invoices i ON i.appointment_id = a.appointment_id GROUP BY a.veterinarian_id) sub WHERE v.veterinarian_id = sub.veterinarian_id"
            )
            # rating - synthesize a rating between 3.0 and 5.0 for vets with activity
            vets_all = db.query(models.Veterinarians).all()
            for v in vets_all:
                if getattr(v, 'total_appointments', 0) > 0:
                    # random rating
                    v.rating = Decimal(f"{random.uniform(3.0, 5.0):.2f}")
            db.commit()

            # pets metrics
            conn.execute(
                "UPDATE pets p SET visit_count = sub.cnt, last_visit_date = sub.lastv FROM (SELECT pet_id, COUNT(*) AS cnt, MAX(appointment_date)::date AS lastv FROM appointments WHERE status = 'completed' GROUP BY pet_id) sub WHERE p.pet_id = sub.pet_id"
            )
            db.commit()

        print(f"Post-migration ({migration}) seed: {len(vets)} vets, {len(owners)} owners, {len(pets)} pets, {len(appointments)} appointments")

    except Exception as e:
        print("Error during post-migration seed:", e)
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Seed additional data after migration')
    parser.add_argument('--migration', type=int, default=0, help='Migration number (e.g., 5)')
    parser.add_argument('--yes', action='store_true', help='Proceed even if DB already has data')
    args = parser.parse_args()

    # preflight
    db = SessionLocal()
    try:
        counts = preflight_check(db)
    except Exception as e:
        print(e)
        db.close()
        sys.exit(1)

    if not args.yes and any(v > 0 for v in counts.values()):
        print("Aborting: DB already contains data. Rerun with --yes to force post-migration seeding.")
        db.close()
        sys.exit(0)
    db.close()

    seed_after(args.migration)


if __name__ == '__main__':
    main()
