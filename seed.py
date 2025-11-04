from datetime import date, datetime, timedelta
from datetime import datetime, timedelta
import random
from decimal import Decimal

from database import SessionLocal, engine
import models
from sqlalchemy.exc import IntegrityError


def get_or_create_vet(db, data: dict):
    # Prefer license_number, fall back to email
    vet = None
    if data.get('license_number'):
        vet = db.query(models.Veterinarians).filter_by(license_number=data['license_number']).first()
    if not vet and data.get('email'):
        vet = db.query(models.Veterinarians).filter_by(email=data['email']).first()
    if vet:
        return vet
    vet = models.Veterinarians(**data)
    db.add(vet)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # likely a concurrent insert or unique violation; try to fetch existing
        if data.get('license_number'):
            vet = db.query(models.Veterinarians).filter_by(license_number=data['license_number']).first()
        if not vet and data.get('email'):
            vet = db.query(models.Veterinarians).filter_by(email=data['email']).first()
        if vet:
            return vet
        raise
    db.refresh(vet)
    return vet


def get_or_create_owner(db, data: dict):
    # Owners are unique by email when available
    owner = None
    if data.get('email'):
        owner = db.query(models.Owners).filter_by(email=data['email']).first()
    if owner:
        return owner
    owner = models.Owners(**data)
    db.add(owner)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if data.get('email'):
            owner = db.query(models.Owners).filter_by(email=data['email']).first()
        if owner:
            return owner
        raise
    db.refresh(owner)
    return owner


def get_or_create_pet(db, data: dict):
    # Use owner_id + name + birth_date as a reasonable uniqueness key for seeded pets
    pet = db.query(models.Pets).filter_by(owner_id=data.get('owner_id'), name=data.get('name'), birth_date=data.get('birth_date')).first()
    if pet:
        return pet
    pet = models.Pets(**data)
    db.add(pet)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        pet = db.query(models.Pets).filter_by(owner_id=data.get('owner_id'), name=data.get('name'), birth_date=data.get('birth_date')).first()
        if pet:
            return pet
        raise
    db.refresh(pet)
    return pet


def get_or_create_appointment(db, data: dict):
    # Prevent duplicate appointments for the same pet/vet/datetime
    appt = db.query(models.Appointments).filter_by(pet_id=data.get('pet_id'), veterinarian_id=data.get('veterinarian_id'), appointment_date=data.get('appointment_date')).first()
    if appt:
        return appt
    appt = models.Appointments(**data)
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        appt = db.query(models.Appointments).filter_by(pet_id=data.get('pet_id'), veterinarian_id=data.get('veterinarian_id'), appointment_date=data.get('appointment_date')).first()
        if appt:
            return appt
        raise
    db.refresh(appt)
    return appt


def seed():
    """Populate the database with sample data for the veterinary schema.

    Creates:
    - 5 veterinarians
    - 10 owners
    - ~15 pets
    - ~30 appointments (mix of scheduled, completed, cancelled)
    """
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ----- Veterinarians -----
        vets_data = [
            {"license_number": "VET-1001", "first_name": "Ana", "last_name": "Pérez", "email": "ana.perez@example.com", "specialization": "Surgery"},
            {"license_number": "VET-1002", "first_name": "Luis", "last_name": "Martínez", "email": "luis.martinez@example.com", "specialization": "Dermatology"},
            {"license_number": "VET-1003", "first_name": "María", "last_name": "González", "email": "maria.gonzalez@example.com", "specialization": "Dentistry"},
            {"license_number": "VET-1004", "first_name": "Carlos", "last_name": "Ruiz", "email": "carlos.ruiz@example.com", "specialization": "Internal Medicine"},
            {"license_number": "VET-1005", "first_name": "Elena", "last_name": "Soto", "email": "elena.soto@example.com", "specialization": "General"},
        ]
        vets = []
        for v in vets_data:
            obj = get_or_create_vet(db, v)
            vets.append(obj)

        # ----- Owners -----
        owners = []
        for i in range(1, 11):
            odata = dict(
                first_name=f"Owner{i}",
                last_name="Seed",
                email=f"owner{i}@example.com",
                phone=f"+1-555-10{i:03d}",
                address=f"Seed Ave {i}",
            )
            o = get_or_create_owner(db, odata)
            owners.append(o)

        # ----- Pets (~15) -----
        pet_species = ["dog", "cat", "bird", "rabbit", "other"]
        pets = []
        for i in range(1, 16):
            owner = random.choice(owners)
            species = random.choice(pet_species)
            birth_dt = (datetime.utcnow() - timedelta(days=random.randint(200, 4000))).date()
            pdata = dict(
                name=f"Pet{i}",
                species=species,
                breed="Mixed",
                birth_date=birth_dt,
                weight=Decimal(f"{random.uniform(1.5, 30.0):.2f}"),
                owner_id=owner.owner_id,
            )
            p = get_or_create_pet(db, pdata)
            pets.append(p)

        # ----- Appointments (~30) -----
        appointments = []
        now = datetime.utcnow()
        for i in range(30):
            pet = random.choice(pets)
            vet = random.choice(vets)

            # Spread appointments +/- 20 days from now
            offset_days = random.randint(-20, 20)
            offset_minutes = random.choice([0, 15, 30, 45])
            appt_dt = now + timedelta(days=offset_days, minutes=offset_minutes)

            # Random status: scheduled (future), completed (past), cancelled
            if appt_dt > now:
                status = "scheduled"
            else:
                status = random.choices(["completed", "cancelled", "no_show"], weights=[0.7, 0.2, 0.1])[0]

            appt_data = dict(
                pet_id=pet.pet_id,
                veterinarian_id=vet.veterinarian_id,
                appointment_date=appt_dt,
                reason=random.choice(["Checkup", "Vaccination", "Illness", "Grooming", "Follow-up"]),
                status=status,
                notes="Seeded appointment",
            )
            appt = get_or_create_appointment(db, appt_data)
            appointments.append(appt)

        db.commit()
        for a in appointments:
            db.refresh(a)

        print(f"Seeded: {len(vets)} veterinarians, {len(owners)} owners, {len(pets)} pets, {len(appointments)} appointments")

    except Exception as e:
        print("Error while seeding:", e)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
