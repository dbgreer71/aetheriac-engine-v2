"""
Security module for AE v2.

This module provides authentication, authorization, and security utilities
for the Aetheriac Engine v2 API.
"""

from .auth import (
    AuthManager,
    get_current_user,
    get_current_user_optional,
    require_permission,
    require_any_permission,
    require_all_permissions,
    get_auth_manager,
)
from .models import User, Role, Permission
from .middleware import (
    SecurityMiddleware,
    create_cors_middleware,
    InputValidationMiddleware,
    AuditMiddleware,
)
from .utils import SecurityUtils

__all__ = [
    "AuthManager",
    "get_current_user",
    "get_current_user_optional",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "get_auth_manager",
    "User",
    "Role",
    "Permission",
    "SecurityMiddleware",
    "create_cors_middleware",
    "InputValidationMiddleware",
    "AuditMiddleware",
    "SecurityUtils",
]
