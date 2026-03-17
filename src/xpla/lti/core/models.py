"""SQLModel definitions for LTI 1.3 tool provider."""

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint


class Platform(SQLModel, table=True):
    __tablename__ = "platform"
    __table_args__ = (UniqueConstraint("issuer", "client_id"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str
    issuer: str
    client_id: str
    oidc_auth_url: str
    jwks_url: str
    access_token_url: str = ""


class Deployment(SQLModel, table=True):
    __tablename__ = "deployment"

    id: int | None = Field(default=None, primary_key=True)
    platform_id: int = Field(foreign_key="platform.id")
    deployment_id: str


class Nonce(SQLModel, table=True):
    __tablename__ = "nonce"

    id: int | None = Field(default=None, primary_key=True)
    value: str
    platform_id: int = Field(foreign_key="platform.id")
    expires_at: datetime
