import re

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Guardian, User
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api", tags=["account"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_GUARDIANS = 10
BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
GENDERS = {"Female", "Male", "Other", "Prefer not to say"}


def _phone_digits(phone: str) -> str:
    """Local mobile number without +91 / leading 0, for validation and comparison."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits.lstrip("0") if len(digits) == 11 else digits


def _valid_phone(phone: str) -> bool:
    return len(_phone_digits(phone)) == 10


def _guardian_rows(items):
    rows = []
    for item in items[:MAX_GUARDIANS]:
        phone = str(item.get("phone", "")).strip()
        if not phone:
            continue
        extra = {k: v for k, v in item.items() if k not in ("name", "phone", "relation")}
        rows.append(
            Guardian(
                position=len(rows),
                name=str(item.get("name", "")).strip()[:120],
                phone=phone[:32],
                relation=str(item.get("relation") or "Guardian")[:60],
                extra=extra,
            )
        )
    return rows


def _fail(message: str, code: int = 400):
    return JSONResponse({"success": False, "error": message}, status_code=code)


class RegisterIn(BaseModel):
    email: str = ""
    password: str = ""
    name: str = ""
    phone: str = ""
    gender: str = ""
    blood_group: str = ""
    date_of_birth: str = ""
    address: str = ""
    medical_notes: str = ""
    guardians: list[dict] = []


class LoginIn(BaseModel):
    email: str = ""
    password: str = ""


class ProfileIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    gender: str | None = None
    blood_group: str | None = None
    date_of_birth: str | None = None
    address: str | None = None
    medical_notes: str | None = None


class GuardiansIn(BaseModel):
    guardians: list[dict] = []


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        return _fail("Enter a valid email address")
    if len(body.password) < 6:
        return _fail("Password must be at least 6 characters")
    if not body.name.strip():
        return _fail("Name is required")
    if not _valid_phone(body.phone):
        return _fail("Enter your 10-digit mobile number")
    if body.gender not in GENDERS:
        return _fail("Select your gender")
    if body.blood_group not in BLOOD_GROUPS:
        return _fail("Select your blood group")
    if body.date_of_birth and not DATE_RE.match(body.date_of_birth):
        return _fail("Date of birth must look like 1998-04-21")
    guardians = _guardian_rows(body.guardians)
    if not guardians:
        return _fail("Add at least one emergency contact")
    for g in guardians:
        if not g.name:
            return _fail("Every emergency contact needs a name")
        if not _valid_phone(g.phone):
            return _fail(f"Enter a valid 10-digit number for {g.name}")
        if _phone_digits(g.phone) == _phone_digits(body.phone):
            return _fail("An emergency contact can't use your own number")
    if db.scalar(select(User).where(User.email == email)):
        return _fail("An account with this email already exists", 409)

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        name=body.name.strip()[:120],
        phone=body.phone.strip()[:32],
        gender=body.gender,
        blood_group=body.blood_group,
        date_of_birth=body.date_of_birth,
        address=body.address.strip()[:300],
        medical_notes=body.medical_notes.strip()[:500],
        guardians=guardians,
    )
    db.add(user)
    db.commit()
    return {"success": True, "token": create_token(user.id), "user": user.to_dict()}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not verify_password(body.password, user.password_hash):
        return _fail("Incorrect email or password", 401)
    return {"success": True, "token": create_token(user.id), "user": user.to_dict()}


@router.get("/user/profile")
def profile(user: User = Depends(current_user)):
    return {"success": True, "user": user.to_dict()}


@router.put("/user/profile")
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for field in ("name", "phone", "gender", "blood_group", "date_of_birth", "address", "medical_notes"):
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value.strip())
    db.commit()
    return {"success": True, "user": user.to_dict()}


@router.post("/user/guardians")
def update_guardians(body: GuardiansIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.guardians = _guardian_rows(body.guardians)
    db.commit()
    return {"success": True, "guardians": [g.to_dict() for g in user.guardians]}


@router.delete("/user")
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"success": True}
