"""
Authentication manager for AE v2.

This module provides JWT-based authentication and user management.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from .models import (
    User,
    Role,
    Permission,
    TokenData,
    LoginRequest,
    LoginResponse,
    SecurityConfig,
    create_default_user,
    get_role_permissions,
)

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


class AuthManager:
    """Authentication and authorization manager."""

    def __init__(self, config: SecurityConfig):
        """Initialize the authentication manager."""
        self.config = config
        self.users: Dict[str, User] = {}
        self.login_attempts: Dict[str, List[datetime]] = {}
        self.locked_accounts: Dict[str, datetime] = {}

        # Initialize default users
        self._initialize_default_users()

    def _initialize_default_users(self) -> None:
        """Initialize default users for development."""
        # Create admin user
        admin_user = create_default_user(
            username="admin", email="admin@aetheriac.local", role=Role.ADMIN
        )
        admin_user.set_password("admin123456")
        self.users[admin_user.id] = admin_user

        # Create operator user
        operator_user = create_default_user(
            username="operator", email="operator@aetheriac.local", role=Role.OPERATOR
        )
        operator_user.set_password("operator123456")
        self.users[operator_user.id] = operator_user

        # Create viewer user
        viewer_user = create_default_user(
            username="viewer", email="viewer@aetheriac.local", role=Role.VIEWER
        )
        viewer_user.set_password("viewer123456")
        self.users[viewer_user.id] = viewer_user

        logger.info("Initialized default users: admin, operator, viewer")

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        # Check if account is locked
        if self._is_account_locked(username):
            logger.warning(f"Login attempt for locked account: {username}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to too many failed attempts",
            )

        # Find user by username
        user = self._get_user_by_username(username)
        if not user:
            self._record_failed_attempt(username)
            return None

        # Verify password
        if not user.verify_password(password):
            self._record_failed_attempt(username)
            return None

        # Clear failed attempts on successful login
        self._clear_failed_attempts(username)

        # Update last login
        user.update_last_login()

        logger.info(f"Successful login for user: {username}")
        return user

    def create_access_token(self, user: User) -> str:
        """Create a JWT access token for a user."""
        expiration = datetime.utcnow() + timedelta(
            minutes=self.config.access_token_expire_minutes
        )

        token_data = TokenData(
            user_id=user.id,
            username=user.username,
            role=user.role,
            permissions=user.permissions,
            exp=expiration,
        )

        # Convert to dict for JWT encoding
        payload = token_data.model_dump()
        # Convert set to list for JSON serialization
        payload["permissions"] = list(payload["permissions"])
        payload["exp"] = expiration
        payload["iat"] = datetime.utcnow()

        token = jwt.encode(
            payload, self.config.secret_key, algorithm=self.config.algorithm
        )

        return token

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token, self.config.secret_key, algorithms=[self.config.algorithm]
            )

            # Convert back to TokenData
            token_data = TokenData(**payload)

            # Check if user still exists and is active
            user = self.users.get(token_data.user_id)
            if not user or not user.is_active:
                return None

            return token_data

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except ValidationError as e:
            logger.warning(f"Token data validation failed: {e}")
            return None

    def login(self, login_request: LoginRequest) -> LoginResponse:
        """Process user login and return access token."""
        user = self.authenticate_user(login_request.username, login_request.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = self.create_access_token(user)

        # Convert user to dict and handle set serialization
        user_dict = user.model_dump()
        user_dict["permissions"] = list(user_dict["permissions"])

        return LoginResponse(
            access_token=access_token,
            expires_in=self.config.access_token_expire_minutes * 60,
            user=user,
        )

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self._get_user_by_username(username)

    def create_user(self, username: str, email: str, role: Role, password: str) -> User:
        """Create a new user."""
        # Check if username already exists
        if self._get_user_by_username(username):
            raise ValueError(f"Username {username} already exists")

        # Check if email already exists
        if self._get_user_by_email(email):
            raise ValueError(f"Email {email} already exists")

        # Validate password
        if len(password) < self.config.password_min_length:
            raise ValueError(
                f"Password must be at least {self.config.password_min_length} characters"
            )

        # Create user
        user = create_default_user(username, email, role)
        user.set_password(password)

        self.users[user.id] = user
        logger.info(f"Created new user: {username} with role {role}")

        return user

    def update_user_role(self, user_id: str, new_role: Role) -> User:
        """Update user role and permissions."""
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user.role = new_role
        user.permissions = get_role_permissions(new_role)

        logger.info(f"Updated user {user.username} role to {new_role}")
        return user

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user."""
        user = self.users.get(user_id)
        if not user:
            return False

        user.is_active = False
        logger.info(f"Deactivated user: {user.username}")
        return True

    def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())

    def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (case-insensitive)."""
        username_lower = username.lower()
        for user in self.users.values():
            if user.username.lower() == username_lower:
                return user
        return None

    def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        email_lower = email.lower()
        for user in self.users.values():
            if user.email.lower() == email_lower:
                return user
        return None

    def _record_failed_attempt(self, username: str) -> None:
        """Record a failed login attempt."""
        now = datetime.utcnow()

        if username not in self.login_attempts:
            self.login_attempts[username] = []

        self.login_attempts[username].append(now)

        # Keep only recent attempts
        cutoff = now - timedelta(minutes=self.config.lockout_duration_minutes)
        self.login_attempts[username] = [
            attempt for attempt in self.login_attempts[username] if attempt > cutoff
        ]

        # Check if account should be locked
        if len(self.login_attempts[username]) >= self.config.max_login_attempts:
            self.locked_accounts[username] = now
            logger.warning(f"Account locked for user: {username}")

    def _clear_failed_attempts(self, username: str) -> None:
        """Clear failed login attempts for a user."""
        if username in self.login_attempts:
            del self.login_attempts[username]
        if username in self.locked_accounts:
            del self.locked_accounts[username]

    def _is_account_locked(self, username: str) -> bool:
        """Check if an account is locked."""
        if username not in self.locked_accounts:
            return False

        lockout_time = self.locked_accounts[username]
        lockout_duration = timedelta(minutes=self.config.lockout_duration_minutes)

        if datetime.utcnow() - lockout_time > lockout_duration:
            # Unlock account
            del self.locked_accounts[username]
            return False

        return True

    def save_users_to_file(self, file_path: Path) -> None:
        """Save users to a JSON file."""
        users_data = []
        for user in self.users.values():
            user_dict = user.dict()
            # Don't save password hashes in plain text
            if "password_hash" in user_dict:
                del user_dict["password_hash"]
            users_data.append(user_dict)

        with open(file_path, "w") as f:
            json.dump(users_data, f, indent=2, default=str)

        logger.info(f"Saved {len(users_data)} users to {file_path}")

    def load_users_from_file(self, file_path: Path) -> None:
        """Load users from a JSON file."""
        if not file_path.exists():
            logger.warning(f"Users file not found: {file_path}")
            return

        with open(file_path, "r") as f:
            users_data = json.load(f)

        for user_data in users_data:
            try:
                user = User(**user_data)
                self.users[user.id] = user
            except Exception as e:
                logger.error(
                    f"Failed to load user {user_data.get('username', 'unknown')}: {e}"
                )

        logger.info(f"Loaded {len(users_data)} users from {file_path}")


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the global authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        # Create default config for development
        config = SecurityConfig(
            secret_key="your-super-secret-key-change-in-production-32-chars-min",
            algorithm="HS256",
            access_token_expire_minutes=30,
        )
        _auth_manager = AuthManager(config)
    return _auth_manager


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> User:
    """Get the current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = auth_manager.verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_manager.get_user(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> Optional[User]:
    """Get the current authenticated user (optional)."""
    if not credentials:
        return None

    token_data = auth_manager.verify_token(credentials.credentials)
    if not token_data:
        return None

    return auth_manager.get_user(token_data.user_id)


def require_permission(permission: Permission):
    """Decorator to require a specific permission."""

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user

    return permission_checker


def require_any_permission(permissions: List[Permission]):
    """Decorator to require any of the specified permissions."""

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_any_permission(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires one of {permissions}",
            )
        return current_user

    return permission_checker


def require_all_permissions(permissions: List[Permission]):
    """Decorator to require all of the specified permissions."""

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_all_permissions(permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires all of {permissions}",
            )
        return current_user

    return permission_checker
