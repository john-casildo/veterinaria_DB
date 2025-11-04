from datetime import datetime, timedelta
import random
from decimal import Decimal

from database import SessionLocal, engine
import models
from seed import get_or_create_vet, get_or_create_owner, get_or_create_pet, get_or_create_appointment
import sys
import argparse


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


def seed_initial():
    """Seed initial dataset: 10 veterinarians, 20 owners, 30 pets, 50 appointments."""
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        vets = []
        for i in range(1, 11):
            vdata = dict(
                license_number=f"VET-2{i:03d}",
                first_name=f"Vet{i}",
                last_name="Seed",
                email=f"vet{i}@example.com",
                specialization=random.choice(["General", "Surgery", "Dentistry", "Dermatology", "Internal Medicine"]),
            )
            vets.append(get_or_create_vet(db, vdata))

        owners = []
        for i in range(1, 21):
            odata = dict(
                first_name=f"Owner{i}",
                last_name="Initial",
                email=f"initial_owner{i}@example.com",
                phone=f"+1-555-20{i:03d}",
                address=f"Initial St {i}",
            )
            owners.append(get_or_create_owner(db, odata))

        pets = []
        species = ["dog", "cat", "bird", "rabbit", "other"]
        for i in range(1, 31):
            owner = random.choice(owners)
            birth_dt = (datetime.utcnow() - timedelta(days=random.randint(365, 4000))).date()
            pdata = dict(
                name=f"InitPet{i}",
                species=random.choice(species),
                breed="Mixed",
                birth_date=birth_dt,
                weight=Decimal(f"{random.uniform(1.0, 40.0):.2f}"),
                owner_id=owner.owner_id,
            )
            pets.append(get_or_create_pet(db, pdata))

        appointments = []
        now = datetime.utcnow()
        for i in range(50):
            pet = random.choice(pets)
            vet = random.choice(vets)
            offset_days = random.randint(-90, 30)
            offset_minutes = random.choice([0, 15, 30, 45])
            appt_dt = now + timedelta(days=offset_days, minutes=offset_minutes)
            status = "scheduled" if appt_dt > now else random.choices(["completed", "cancelled", "no_show"], weights=[0.75, 0.15, 0.10])[0]
            adata = dict(
                pet_id=pet.pet_id,
                veterinarian_id=vet.veterinarian_id,
                appointment_date=appt_dt,
                reason=random.choice(["Checkup", "Vaccination", "Illness", "Grooming", "Follow-up"]),
                status=status,
                notes="Initial seed appointment",
            )
            appointments.append(get_or_create_appointment(db, adata))

        print(f"Initial seed: {len(vets)} vets, {len(owners)} owners, {len(pets)} pets, {len(appointments)} appointments")

    except Exception as e:
        print("Error during initial seed:", e)
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Run initial seed dataset')
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
        print("Aborting: DB already contains data. Rerun with --yes to force seeding.")
        db.close()
        sys.exit(0)
    db.close()

    seed_initial()


if __name__ == "__main__":
    main()
