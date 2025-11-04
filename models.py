from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Numeric, Text, DateTime, Date, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Veterinarians(Base):
    __tablename__ = "veterinarians"

    veterinarian_id = Column(Integer, primary_key=True, index=True)
    license_number = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    specialization = Column(String(200), nullable=True)
    hire_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    # Appointments assigned
    appointments = relationship("Appointments", back_populates="veterinarian", cascade="all, delete-orphan")


class Owners(Base):
    __tablename__ = "owners"

    owner_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    registration_date = Column(DateTime, server_default=func.now(), nullable=False)
    # One owner -> many pets
    pets = relationship("Pets", back_populates="owner", cascade="all, delete-orphan")


class Pets(Base):
    __tablename__ = "pets"

    pet_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    species = Column(Enum('dog', 'cat', 'bird', 'rabbit', 'other', name='pet_species'), nullable=False)
    breed = Column(String(100), nullable=True)
    birth_date = Column(Date, nullable=True)
    weight = Column(Numeric(6, 2), nullable=False)
    owner_id = Column(Integer, ForeignKey("owners.owner_id"), nullable=False, index=True)
    registration_date = Column(DateTime, server_default=func.now(), nullable=False)
    # Relationships
    owner = relationship("Owners", back_populates="pets")
    appointments = relationship("Appointments", back_populates="pet", cascade="all, delete-orphan")


class Appointments(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, index=True)
    pet_id = Column(Integer, ForeignKey("pets.pet_id"), nullable=False, index=True)
    veterinarian_id = Column(Integer, ForeignKey("veterinarians.veterinarian_id"), nullable=False, index=True)
    appointment_date = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum('scheduled', 'completed', 'cancelled', 'no_show', name='appointment_status'), nullable=False, default='scheduled', index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    # relationships
    pet = relationship("Pets", back_populates="appointments")
    veterinarian = relationship("Veterinarians", back_populates="appointments")


# Indexes for new tables
Index('ix_pets_owner', Pets.owner_id)
Index('ix_appointments_vet_status', Appointments.veterinarian_id, Appointments.status)
    
