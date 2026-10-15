from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 10:
        raise ValueError("Phone number must be 10 digits")
    return digits


class PatientBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: str = Field(..., min_length=8, max_length=10)
    sex: str
    phone_number: str
    email: Optional[str] = None
    address_line_1: str = Field(..., min_length=1, max_length=255)
    address_line_2: Optional[str] = None
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., min_length=5, max_length=10)
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: str = "English"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z'\- ]+", value.strip()):
            raise ValueError("Name contains invalid characters")
        return value.strip()

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: str) -> str:
        try:
            dob = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError("Date of birth must be in YYYY-MM-DD format") from exc
        if dob > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        valid_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
        }
        state = value.strip().upper()
        if state not in valid_states:
            raise ValueError("State must be a valid US state code")
        return state

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, value: str) -> str:
        zip_value = value.strip()
        if not re.fullmatch(r"\d{5}(?:-\d{4})?", zip_value):
            raise ValueError("ZIP code must be 5 digits or ZIP+4")
        return zip_value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value.strip()):
            raise ValueError("Invalid email format")
        return value.strip()


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return PatientBase.validate_name(value)

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return PatientBase.validate_dob(value)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return normalize_phone(value)

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return PatientBase.validate_state(value)

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return PatientBase.validate_zip(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        return PatientBase.validate_email(value)


class PatientOut(PatientBase):
    patient_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class APIResponse(BaseModel):
    data: dict
    error: Optional[str] = None
