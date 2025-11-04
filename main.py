from fastapi import FastAPI, HTTPException, Depends
from datetime import date, datetime
import models
from typing import List, Annotated, ClassVar, Optional
from database import SessionLocal, engine
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError


from schemas import (
    VeterinarianCreate,
    VeterinarianRead,
    OwnerCreate,
    OwnerRead,
    PetCreate,
    PetRead,
    AppointmentCreate,
    AppointmentRead,
    OwnerWithPets,
    PetWithAppointments,
)



app = FastAPI(title="Veterinary Clinic Management API", version="1.0.0")
models.Base.metadata.create_all(bind=engine)


def get_db():
		db = SessionLocal()
		try:
			yield db
		finally:
			db.close()

db_dependency = Annotated[Session, Depends(get_db)]


# ---------------- Veterinary / Owners / Pets / Appointments Endpoints ----------------

# -- Veterinarians
@app.get("/veterinarians", response_model=List[VeterinarianRead])
def list_veterinarians(db: Session = Depends(get_db)):
    return db.query(models.Veterinarians).all()


@app.get("/veterinarians/{vet_id}", response_model=VeterinarianRead)
def get_veterinarian(vet_id: int, db: Session = Depends(get_db)):
    v = db.query(models.Veterinarians).get(vet_id)
    if not v:
        raise HTTPException(404, "Veterinarian not found")
    return v


@app.get("/veterinarians/{vet_id}/appointments", response_model=List[AppointmentRead])
def get_vet_appointments(vet_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Veterinarians).get(vet_id):
        raise HTTPException(404, "Veterinarian not found")
    return db.query(models.Appointments).filter(models.Appointments.veterinarian_id == vet_id).all()


@app.get("/veterinarians/{vet_id}/schedule", response_model=List[AppointmentRead])
def get_vet_schedule(vet_id: int, date: Optional[date] = None, db: Session = Depends(get_db)):
    if not db.query(models.Veterinarians).get(vet_id):
        raise HTTPException(404, "Veterinarian not found")
    q = db.query(models.Appointments).filter(models.Appointments.veterinarian_id == vet_id)
    if date is not None:
        q = q.filter(func.date(models.Appointments.appointment_date) == date)
    return q.order_by(models.Appointments.appointment_date).all()


@app.post("/veterinarians", response_model=VeterinarianRead)
def create_veterinarian(payload: VeterinarianCreate, db: Session = Depends(get_db)):
    # uniqueness checks
    if db.query(models.Veterinarians).filter(models.Veterinarians.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.Veterinarians).filter(models.Veterinarians.license_number == payload.license_number).first():
        raise HTTPException(status_code=400, detail="License number already used")
    v = models.Veterinarians(**payload.dict(exclude_unset=True))
    db.add(v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflict creating veterinarian")
    db.refresh(v)
    return v


@app.put("/veterinarians/{vet_id}", response_model=VeterinarianRead)
def replace_veterinarian(vet_id: int, payload: VeterinarianCreate, db: Session = Depends(get_db)):
    v = db.query(models.Veterinarians).get(vet_id)
    if not v:
        raise HTTPException(404, "Veterinarian not found")
    for k, val in payload.dict(exclude_unset=True).items():
        setattr(v, k, val)
    db.commit()
    return v


@app.delete("/veterinarians/{vet_id}")
def delete_veterinarian(vet_id: int, db: Session = Depends(get_db)):
    v = db.query(models.Veterinarians).get(vet_id)
    if not v:
        raise HTTPException(404, "Veterinarian not found")
    # do not allow removal if future appointments exist
    future = db.query(models.Appointments).filter(models.Appointments.veterinarian_id == vet_id, models.Appointments.appointment_date >= datetime.utcnow()).first()
    if future:
        raise HTTPException(status_code=400, detail="Veterinarian has upcoming appointments and cannot be deleted")
    db.delete(v)
    db.commit()
    return {"detail": "Veterinarian deleted"}


# -- Owners
@app.get("/owners", response_model=List[OwnerRead])
def list_owners(db: Session = Depends(get_db)):
    return db.query(models.Owners).all()


@app.get("/owners/{owner_id}", response_model=OwnerRead)
def get_owner(owner_id: int, db: Session = Depends(get_db)):
    o = db.query(models.Owners).get(owner_id)
    if not o:
        raise HTTPException(404, "Owner not found")
    return o


@app.get("/owners/{owner_id}/pets", response_model=List[PetRead])
def get_owner_pets(owner_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Owners).get(owner_id):
        raise HTTPException(404, "Owner not found")
    return db.query(models.Pets).filter(models.Pets.owner_id == owner_id).all()


@app.get("/owners/{owner_id}/appointments", response_model=List[AppointmentRead])
def get_owner_appointments(owner_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Owners).get(owner_id):
        raise HTTPException(404, "Owner not found")
    return db.query(models.Appointments).join(models.Pets).filter(models.Pets.owner_id == owner_id).all()


@app.post("/owners", response_model=OwnerRead)
def create_owner(payload: OwnerCreate, db: Session = Depends(get_db)):
    if db.query(models.Owners).filter(models.Owners.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    o = models.Owners(**payload.dict(exclude_unset=True))
    db.add(o)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflict creating owner")
    db.refresh(o)
    return o


@app.put("/owners/{owner_id}", response_model=OwnerRead)
def replace_owner(owner_id: int, payload: OwnerCreate, db: Session = Depends(get_db)):
    o = db.query(models.Owners).get(owner_id)
    if not o:
        raise HTTPException(404, "Owner not found")
    for k, val in payload.dict(exclude_unset=True).items():
        setattr(o, k, val)
    db.commit()
    return o


@app.delete("/owners/{owner_id}")
def delete_owner(owner_id: int, db: Session = Depends(get_db)):
    o = db.query(models.Owners).get(owner_id)
    if not o:
        raise HTTPException(404, "Owner not found")
    # prevent deleting if owner has pets
    has_pets = db.query(models.Pets).filter(models.Pets.owner_id == owner_id).first()
    if has_pets:
        raise HTTPException(status_code=400, detail="Owner has pets and cannot be deleted")
    db.delete(o)
    db.commit()
    return {"detail": "Owner deleted"}


# -- Pets
@app.get("/pets", response_model=List[PetRead])
def list_pets(db: Session = Depends(get_db)):
    return db.query(models.Pets).all()


@app.get("/pets/{pet_id}", response_model=PetRead)
def get_pet(pet_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Pets).get(pet_id)
    if not p:
        raise HTTPException(404, "Pet not found")
    return p


@app.get("/pets/{pet_id}/medical-history")
def get_pet_medical_history(pet_id: int, db: Session = Depends(get_db)):
    # Placeholder: requires medical records migration
    raise HTTPException(status_code=501, detail="Medical records require migration")


@app.get("/pets/{pet_id}/vaccinations")
def get_pet_vaccinations(pet_id: int, db: Session = Depends(get_db)):
    # Placeholder: requires vaccinations migration
    raise HTTPException(status_code=501, detail="Vaccination records require migration")


@app.post("/pets", response_model=PetRead)
def create_pet(payload: PetCreate, db: Session = Depends(get_db)):
    # validate owner exists
    if not db.query(models.Owners).get(payload.owner_id):
        raise HTTPException(status_code=400, detail="Owner not found")
    p = models.Pets(**payload.dict(exclude_unset=True))
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflict creating pet")
    db.refresh(p)
    return p


@app.put("/pets/{pet_id}", response_model=PetRead)
def replace_pet(pet_id: int, payload: PetCreate, db: Session = Depends(get_db)):
    p = db.query(models.Pets).get(pet_id)
    if not p:
        raise HTTPException(404, "Pet not found")
    for k, val in payload.dict(exclude_unset=True).items():
        setattr(p, k, val)
    db.commit()
    return p


@app.delete("/pets/{pet_id}")
def delete_pet(pet_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Pets).get(pet_id)
    if not p:
        raise HTTPException(404, "Pet not found")
    # prevent deleting if future appointments
    future = db.query(models.Appointments).filter(models.Appointments.pet_id == pet_id, models.Appointments.appointment_date >= datetime.utcnow()).first()
    if future:
        raise HTTPException(status_code=400, detail="Pet has upcoming appointments and cannot be deleted")
    db.delete(p)
    db.commit()
    return {"detail": "Pet deleted"}


# -- Appointments
@app.get("/appointments", response_model=List[AppointmentRead])
def list_appointments(db: Session = Depends(get_db)):
    return db.query(models.Appointments).all()


@app.get("/appointments/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    a = db.query(models.Appointments).get(appointment_id)
    if not a:
        raise HTTPException(404, "Appointment not found")
    return a


@app.get("/appointments/today", response_model=List[AppointmentRead])
def get_appointments_today(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    return db.query(models.Appointments).filter(func.date(models.Appointments.appointment_date) == today).all()


@app.get("/appointments/pending", response_model=List[AppointmentRead])
def get_pending_appointments(db: Session = Depends(get_db)):
    return db.query(models.Appointments).filter(models.Appointments.status == 'scheduled').all()


@app.post("/appointments", response_model=AppointmentRead)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    # validate pet and vet
    pet = db.query(models.Pets).get(payload.pet_id)
    if not pet:
        raise HTTPException(status_code=400, detail="Pet not found")
    vet = db.query(models.Veterinarians).get(payload.veterinarian_id)
    if not vet:
        raise HTTPException(status_code=400, detail="Veterinarian not found")
    # appointment_date should be present and not in the past
    if payload.appointment_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Appointment date must be in the future")
    new = models.Appointments(**payload.dict(exclude_unset=True))
    db.add(new)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflict creating appointment")
    db.refresh(new)
    return new


@app.put("/appointments/{appointment_id}", response_model=AppointmentRead)
def replace_appointment(appointment_id: int, payload: AppointmentCreate, db: Session = Depends(get_db)):
    a = db.query(models.Appointments).get(appointment_id)
    if not a:
        raise HTTPException(404, "Appointment not found")
    for k, val in payload.dict(exclude_unset=True).items():
        setattr(a, k, val)
    db.commit()
    return a


@app.put("/appointments/{appointment_id}/complete", response_model=AppointmentRead)
def complete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    a = db.query(models.Appointments).get(appointment_id)
    if not a:
        raise HTTPException(404, "Appointment not found")
    if a.status == 'completed':
        raise HTTPException(status_code=400, detail="Appointment already completed")
    a.status = 'completed'
    db.commit()
    return a


@app.put("/appointments/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    a = db.query(models.Appointments).get(appointment_id)
    if not a:
        raise HTTPException(404, "Appointment not found")
    if a.status in ['cancelled', 'completed']:
        raise HTTPException(status_code=400, detail="Appointment cannot be cancelled")
    a.status = 'cancelled'
    db.commit()
    return a


@app.delete("/appointments/{appointment_id}")
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    a = db.query(models.Appointments).get(appointment_id)
    if not a:
        raise HTTPException(404, "Appointment not found")
    db.delete(a)
    db.commit()
    return {"detail": "Appointment deleted"}


# -- Medical Records / Vaccines / Invoices / Reports placeholders
@app.get("/medical-records")
def list_medical_records():
    raise HTTPException(status_code=501, detail="Medical records require migration 1")


@app.get("/vaccines")
def list_vaccines():
    raise HTTPException(status_code=501, detail="Vaccines require migration 2")


@app.get("/invoices")
def list_invoices():
    raise HTTPException(status_code=501, detail="Invoices require migration 4")


@app.get("/reports/revenue")
def report_revenue(start_date: Optional[date] = None, end_date: Optional[date] = None):
    raise HTTPException(status_code=501, detail="Reports require all migrations")



