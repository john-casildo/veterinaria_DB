from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import date, datetime


# ---------------- Veterinary Pydantic Schemas ----------------


class VeterinarianBase(BaseModel):
    license_number: str = Field(..., max_length=50)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    specialization: Optional[str] = Field(None, max_length=200)
    hire_date: Optional[date] = None
    is_active: Optional[bool] = True


class VeterinarianCreate(VeterinarianBase):
    pass


class VeterinarianRead(VeterinarianBase):
    veterinarian_id: int

    model_config = ConfigDict(from_attributes=True)


class OwnerBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None


class OwnerCreate(OwnerBase):
    pass


class OwnerRead(OwnerBase):
    owner_id: int
    registration_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PetBase(BaseModel):
    name: str = Field(..., max_length=100)
    species: Literal['dog', 'cat', 'bird', 'rabbit', 'other']
    breed: Optional[str] = Field(None, max_length=100)
    birth_date: Optional[date] = None
    weight: float
    owner_id: int


class PetCreate(PetBase):
    pass


class PetRead(PetBase):
    pet_id: int
    registration_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentBase(BaseModel):
    pet_id: int
    veterinarian_id: int
    appointment_date: datetime
    reason: str
    status: Literal['scheduled', 'completed', 'cancelled', 'no_show'] = 'scheduled'
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentRead(AppointmentBase):
    appointment_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Collections / nested views
class OwnerWithPets(OwnerRead):
    pets: List[PetRead] = []


class PetWithAppointments(PetRead):
    appointments: List[AppointmentRead] = []
