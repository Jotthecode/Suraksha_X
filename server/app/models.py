import datetime as dt
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def new_id():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    gender: Mapped[str] = mapped_column(String(32), default="Female")
    blood_group: Mapped[str] = mapped_column(String(8), default="O+")
    date_of_birth: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD
    address: Mapped[str] = mapped_column(String(300), default="")
    medical_notes: Mapped[str] = mapped_column(String(500), default="")  # allergies, conditions, medicines
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    guardians: Mapped[list["Guardian"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Guardian.position"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "phone": self.phone,
            "gender": self.gender,
            "blood_group": self.blood_group,
            "date_of_birth": self.date_of_birth,
            "address": self.address,
            "medical_notes": self.medical_notes,
            "guardians": [g.to_dict() for g in self.guardians],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(32))
    relation: Mapped[str] = mapped_column(String(60), default="Guardian")
    # Anything else the app stores on a contact (id, flags, …) round-trips untouched
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="guardians")

    def to_dict(self):
        return {**(self.extra or {}), "name": self.name, "phone": self.phone, "relation": self.relation}


class TrackingSession(Base):
    __tablename__ = "tracking_sessions"

    # The id is the secret in the shared link, so it is a 128-bit random hex string
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user_name: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False)

    last_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_battery: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_update: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    points: Mapped[list["LocationPoint"]] = relationship(
        cascade="all, delete-orphan", order_by="LocationPoint.id"
    )


class LocationPoint(Base):
    __tablename__ = "location_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("tracking_sessions.id", ondelete="CASCADE"), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_name: Mapped[str] = mapped_column(String(120), default="")
    trigger: Mapped[str] = mapped_column(String(200), default="SOS")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    nearest_stations: Mapped[list] = mapped_column(JSON, default=list)
    contacts: Mapped[list] = mapped_column(JSON, default=list)
    sms_status: Mapped[list] = mapped_column(JSON, default=list)
    call_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    @property
    def code(self):
        return f"INC-{self.id:06d}"
