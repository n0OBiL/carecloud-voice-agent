from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Patient
from app.schemas import PatientCreate, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


def patient_to_dict(patient: Patient) -> dict:
    return {
        "patient_id": patient.patient_id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "date_of_birth": patient.date_of_birth,
        "sex": patient.sex,
        "phone_number": patient.phone_number,
        "email": patient.email,
        "address_line_1": patient.address_line_1,
        "address_line_2": patient.address_line_2,
        "city": patient.city,
        "state": patient.state,
        "zip_code": patient.zip_code,
        "insurance_provider": patient.insurance_provider,
        "insurance_member_id": patient.insurance_member_id,
        "preferred_language": patient.preferred_language,
        "emergency_contact_name": patient.emergency_contact_name,
        "emergency_contact_phone": patient.emergency_contact_phone,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "updated_at": patient.updated_at.isoformat() if patient.updated_at else None,
        "deleted_at": patient.deleted_at.isoformat() if patient.deleted_at else None,
    }


@router.get("", response_model=dict)
def list_patients(
    db: Session = Depends(get_db),
    last_name: Optional[str] = Query(default=None),
    phone_number: Optional[str] = Query(default=None),
    date_of_birth: Optional[str] = Query(default=None),
):
    query = select(Patient).where(Patient.deleted_at.is_(None))

    if last_name:
        query = query.where(Patient.last_name.ilike(f"%{last_name}%"))
    if phone_number:
        query = query.where(Patient.phone_number == phone_number)
    if date_of_birth:
        query = query.where(Patient.date_of_birth == date_of_birth)

    patients = db.execute(query).scalars().all()
    return {"data": {"patients": [patient_to_dict(p) for p in patients]}, "error": None}


@router.get("/{patient_id}", response_model=dict)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return {"data": patient_to_dict(patient), "error": None}


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(Patient).where(Patient.phone_number == payload.phone_number, Patient.deleted_at.is_(None))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient with this phone number already exists")

    patient = Patient(
        patient_id=str(uuid.uuid4()),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        date_of_birth=payload.date_of_birth,
        sex=payload.sex,
        phone_number=payload.phone_number,
        email=payload.email,
        address_line_1=payload.address_line_1.strip(),
        address_line_2=payload.address_line_2.strip() if payload.address_line_2 else None,
        city=payload.city.strip(),
        state=payload.state.upper(),
        zip_code=payload.zip_code,
        insurance_provider=payload.insurance_provider,
        insurance_member_id=payload.insurance_member_id,
        preferred_language=payload.preferred_language,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {"data": patient_to_dict(patient), "error": None}


@router.put("/{patient_id}", response_model=dict)
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    updates = payload.model_dump(exclude_unset=True)
    if "phone_number" in updates and updates["phone_number"]:
        duplicate = db.execute(
            select(Patient).where(Patient.phone_number == updates["phone_number"], Patient.patient_id != patient_id)
        ).scalar_one_or_none()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another patient already uses this phone number")

    for key, value in updates.items():
        if value is None:
            continue
        if key in {"first_name", "last_name", "address_line_1", "city"}:
            value = value.strip()
        if key == "state" and isinstance(value, str):
            value = value.upper()
        setattr(patient, key, value)

    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)
    return {"data": patient_to_dict(patient), "error": None}


@router.delete("/{patient_id}", response_model=dict)
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    patient.deleted_at = datetime.utcnow()
    patient.updated_at = datetime.utcnow()
    db.commit()
    return {"data": {"message": f"Patient {patient_id} deleted"}, "error": None}
