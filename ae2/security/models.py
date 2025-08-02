"""
Security models for AE v2.

This module defines the data models for authentication and authorization.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Set
from pydantic import BaseModel, Field, validator
import hashlib
import secrets


class Permission(str, Enum):
    """Available permissions in the system."""

    # Read permissions
    READ_HEALTH = "read:health"
    READ_METRICS = "read:metrics"
    READ_QUERY = "read:query"
    READ_CONCEPTS = "read:concepts"
    READ_PLAYBOOKS = "read:playbooks"

    # Write permissions
    WRITE_CONCEPTS = "write:concepts"
    WRITE_PLAYBOOKS = "write:playbooks"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_DEBUG = "admin:debug"


class Role(str, Enum):
    """Available roles in the system."""

    VIEWER = "viewer"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    ADMIN = "admin"


class User(BaseModel):
    """User model for authentication and authorization."""

    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="User email address")
    role: Role = Field(default=Role.VIEWER, description="User role")
    permissions: Set[Permission] = Field(
        default_factory=set, description="User permissions"
    )
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    password_hash: Optional[str] = Field(None, description="Hashed password")

    @validator("email")
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    @validator("username")
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.isalnum() and not all(c in "_-" for c in v if not c.isalnum()):
            raise ValueError("Username must be alphanumeric with only _ or - allowed")
        return v.lower()

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        if not self.is_active:
            return False

        # Admin role has all permissions
        if self.role == Role.ADMIN:
            return True

        return permission in self.permissions

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(self.has_permission(p) for p in permissions)

    def set_password(self, password: str) -> None:
        """Set user password with secure hashing."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()
        self.password_hash = f"{salt}:{password_hash}"

    def verify_password(self, password: str) -> bool:
        """Verify user password."""
        if not self.password_hash:
            return False

        try:
            salt, stored_hash = self.password_hash.split(":", 1)
            password_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            ).hex()
            return secrets.compare_digest(password_hash, stored_hash)
        except (ValueError, AttributeError):
            return False

    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), set: lambda v: list(v)}


class TokenData(BaseModel):
    """Token data model for JWT payload."""

    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    role: Role = Field(..., description="User role")
    permissions: Set[Permission] = Field(
        default_factory=set, description="User permissions"
    )
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(default_factory=datetime.utcnow, description="Issued at time")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), set: lambda v: list(v)}


class LoginRequest(BaseModel):
    """Login request model."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

    @validator("username")
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        return v.lower().strip()

    @validator("password")
    def validate_password(cls, v: str) -> str:
        """Validate password requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: User = Field(..., description="User information")


class PermissionCheck(BaseModel):
    """Permission check request model."""

    permission: Permission = Field(..., description="Permission to check")
    resource: Optional[str] = Field(None, description="Resource identifier")


class SecurityConfig(BaseModel):
    """Security configuration model."""

    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )
    password_min_length: int = Field(default=8, description="Minimum password length")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(
        default=15, description="Account lockout duration"
    )
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    allowed_origins: List[str] = Field(
        default=["*"], description="Allowed CORS origins"
    )
    enable_security_headers: bool = Field(
        default=True, description="Enable security headers"
    )
    enable_content_security_policy: bool = Field(default=True, description="Enable CSP")

    @validator("secret_key")
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @validator("algorithm")
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512"]
        if v not in allowed_algorithms:
            raise ValueError(f"Algorithm must be one of: {allowed_algorithms}")
        return v


# Default role permissions mapping
ROLE_PERMISSIONS = {
    Role.VIEWER: {
        Permission.READ_HEALTH,
        Permission.READ_QUERY,
        Permission.READ_CONCEPTS,
    },
    Role.OPERATOR: {
        Permission.READ_HEALTH,
        Permission.READ_METRICS,
        Permission.READ_QUERY,
        Permission.READ_CONCEPTS,
        Permission.READ_PLAYBOOKS,
        Permission.WRITE_CONCEPTS,
    },
    Role.DEVELOPER: {
        Permission.READ_HEALTH,
        Permission.READ_METRICS,
        Permission.READ_QUERY,
        Permission.READ_CONCEPTS,
        Permission.READ_PLAYBOOKS,
        Permission.WRITE_CONCEPTS,
        Permission.WRITE_PLAYBOOKS,
        Permission.ADMIN_DEBUG,
    },
    Role.ADMIN: {
        Permission.READ_HEALTH,
        Permission.READ_METRICS,
        Permission.READ_QUERY,
        Permission.READ_CONCEPTS,
        Permission.READ_PLAYBOOKS,
        Permission.WRITE_CONCEPTS,
        Permission.WRITE_PLAYBOOKS,
        Permission.ADMIN_USERS,
        Permission.ADMIN_SYSTEM,
        Permission.ADMIN_DEBUG,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def create_default_user(username: str, email: str, role: Role = Role.VIEWER) -> User:
    """Create a default user with role-based permissions."""
    user = User(
        id=secrets.token_urlsafe(16),
        username=username,
        email=email,
        role=role,
        permissions=get_role_permissions(role),
    )
    return user
