from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.database import get_db
from app.models import Patient
from app.schemas import PatientCreate


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 10:
        raise ValueError("Phone number must be 10 digits")
    return digits


def lookup_patient(data: dict[str, Any]) -> dict[str, Any]:
    phone = normalize_phone(data.get("phone_number") or data.get("phone"))
    db = next(get_db())
    try:
        patient = db.execute(
            select(Patient).where(Patient.phone_number == phone, Patient.deleted_at.is_(None))
        ).scalar_one_or_none()
        return {
            "found": patient is not None,
            "patient_id": patient.patient_id if patient else None,
            "message": "Patient found" if patient else "No patient found",
        }
    finally:
        db.close()


def validate_field(data: dict[str, Any]) -> dict[str, Any]:
    field_name = (data.get("field_name") or data.get("name") or "").strip().lower()
    field_value = data.get("field_value") or data.get("value")

    if field_name in {"phone_number", "phone"}:
        try:
            normalized = normalize_phone(field_value)
            return {"valid": True, "normalized_value": normalized}
        except ValueError as exc:
            return {"valid": False, "error": str(exc)}

    if field_name in {"date_of_birth", "dob"}:
        try:
            dob = datetime.strptime(str(field_value), "%Y-%m-%d").date()
        except ValueError:
            return {"valid": False, "error": "DOB must be in YYYY-MM-DD format"}
        if dob > datetime.utcnow().date():
            return {"valid": False, "error": "DOB cannot be in the future"}
        return {"valid": True, "normalized_value": dob.isoformat()}

    if field_name in {"state", "state_code"}:
        state = str(field_value).strip().upper()
        valid = state in {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"}
        return {"valid": valid, "normalized_value": state if valid else None, "error": "Invalid state code" if not valid else None}

    if field_name == "zip_code":
        matches = re.fullmatch(r"\d{5}(?:-\d{4})?", str(field_value).strip())
        return {"valid": bool(matches), "normalized_value": str(field_value).strip() if matches else None, "error": "ZIP code must be 5 digits or ZIP+4" if not matches else None}

    return {"valid": True, "normalized_value": field_value}


def save_patient(data: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = PatientCreate(**data)
    except Exception as exc:  # pragma: no cover - validation path
        return {"success": False, "error": str(exc)}

    db = next(get_db())
    try:
        existing = db.execute(
            select(Patient).where(Patient.phone_number == payload.phone_number, Patient.deleted_at.is_(None))
        ).scalar_one_or_none()
        if existing:
            return {"success": False, "error": "Patient with this phone number already exists"}

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
        return {"success": True, "patient_id": patient.patient_id}
    finally:
        db.close()


def update_patient(data: dict[str, Any]) -> dict[str, Any]:
    patient_id = data.get("patient_id")
    if not patient_id:
        return {"success": False, "error": "patient_id is required"}

    db = next(get_db())
    try:
        patient = db.get(Patient, patient_id)
        if not patient or patient.deleted_at is not None:
            return {"success": False, "error": "Patient not found"}

        updates = data.copy()
        updates.pop("patient_id", None)
        for key, value in updates.items():
            if value is None:
                continue
            if key in {"first_name", "last_name", "address_line_1", "city"} and isinstance(value, str):
                value = value.strip()
            if key == "state" and isinstance(value, str):
                value = value.upper()
            setattr(patient, key, value)

        patient.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(patient)
        return {"success": True, "patient_id": patient.patient_id}
    finally:
        db.close()


def end_call(data: dict[str, Any]) -> dict[str, Any]:
    message = data.get("message") or "Thank you for calling."
    return {"success": True, "message": message, "ended": True}
