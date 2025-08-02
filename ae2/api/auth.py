"""
Authentication API endpoints for AE v2.

This module provides REST API endpoints for authentication and user management.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ..security import (
    AuthManager, get_auth_manager, get_current_user, require_permission,
    require_any_permission, require_all_permissions
)
from ..security.models import (
    User, Role, Permission, LoginRequest, LoginResponse, SecurityConfig
)
from ..security.utils import SecurityUtils

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Security scheme
security = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> LoginResponse:
    """Authenticate user and return access token."""
    try:
        response = auth_manager.login(login_request)
        logger.info(f"Successful login for user: {login_request.username}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for user {login_request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Logout user (client should discard token)."""
    logger.info(f"User logout: {current_user.username}")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user information."""
    return current_user


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> LoginResponse:
    """Refresh access token."""
    try:
        access_token = auth_manager.create_access_token(current_user)
        return LoginResponse(
            access_token=access_token,
            expires_in=auth_manager.config.access_token_expire_minutes * 60,
            user=current_user
        )
    except Exception as e:
        logger.error(f"Token refresh error for user {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> dict:
    """Change user password."""
    # Verify current password
    if not current_user.verify_password(current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    is_valid, issues = SecurityUtils.validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New password is not strong enough: {', '.join(issues)}"
        )
    
    # Update password
    current_user.set_password(new_password)
    
    logger.info(f"Password changed for user: {current_user.username}")
    return {"message": "Password changed successfully"}


# Admin endpoints
@router.get("/users", response_model=List[User])
async def list_users(
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> List[User]:
    """List all users (admin only)."""
    return auth_manager.list_users()


@router.post("/users", response_model=User)
async def create_user(
    username: str,
    email: str,
    role: Role,
    password: str,
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> User:
    """Create a new user (admin only)."""
    try:
        user = auth_manager.create_user(username, email, role, password)
        logger.info(f"User created by {current_user.username}: {username}")
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: Role,
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> User:
    """Update user role (admin only)."""
    try:
        user = auth_manager.update_user_role(user_id, new_role)
        logger.info(f"User role updated by {current_user.username}: {user.username} -> {new_role}")
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating user role {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> dict:
    """Deactivate a user (admin only)."""
    try:
        success = auth_manager.deactivate_user(user_id)
        if success:
            logger.info(f"User deactivated by {current_user.username}: {user_id}")
            return {"message": "User deactivated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        )


@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS)),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> User:
    """Get user by ID (admin only)."""
    user = auth_manager.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


# Security utilities
@router.post("/generate-password")
async def generate_password(
    length: int = 16,
    current_user: User = Depends(require_permission(Permission.ADMIN_USERS))
) -> dict:
    """Generate a secure password (admin only)."""
    try:
        password = SecurityUtils.generate_secure_password(length)
        return {"password": password}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/validate-password")
async def validate_password(password: str) -> dict:
    """Validate password strength."""
    is_valid, issues = SecurityUtils.validate_password_strength(password)
    strength = SecurityUtils.get_password_strength(password)
    entropy = SecurityUtils.calculate_password_entropy(password)
    
    return {
        "is_valid": is_valid,
        "issues": issues,
        "strength": strength,
        "entropy": entropy
    }


@router.get("/permissions")
async def get_permissions(
    current_user: User = Depends(get_current_user)
) -> dict:
    """Get current user permissions."""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "permissions": list(current_user.permissions),
        "is_active": current_user.is_active
    }


@router.post("/check-permission")
async def check_permission(
    permission: Permission,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Check if current user has a specific permission."""
    has_perm = current_user.has_permission(permission)
    return {
        "permission": permission,
        "has_permission": has_perm,
        "user_role": current_user.role
    }


# System security endpoints
@router.get("/security-config")
async def get_security_config(
    current_user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> dict:
    """Get security configuration (admin only)."""
    config = auth_manager.config
    return {
        "algorithm": config.algorithm,
        "access_token_expire_minutes": config.access_token_expire_minutes,
        "password_min_length": config.password_min_length,
        "max_login_attempts": config.max_login_attempts,
        "lockout_duration_minutes": config.lockout_duration_minutes,
        "enable_rate_limiting": config.enable_rate_limiting,
        "rate_limit_requests": config.rate_limit_requests,
        "enable_cors": config.enable_cors,
        "enable_security_headers": config.enable_security_headers,
        "enable_content_security_policy": config.enable_content_security_policy
    }


@router.get("/security-status")
async def get_security_status(
    current_user: User = Depends(require_permission(Permission.ADMIN_SYSTEM)),
    auth_manager: AuthManager = Depends(get_auth_manager)
) -> dict:
    """Get security status information (admin only)."""
    return {
        "total_users": len(auth_manager.users),
        "active_users": len([u for u in auth_manager.users.values() if u.is_active]),
        "locked_accounts": len(auth_manager.locked_accounts),
        "failed_attempts": len(auth_manager.login_attempts),
        "security_features": {
            "rate_limiting": auth_manager.config.enable_rate_limiting,
            "cors": auth_manager.config.enable_cors,
            "security_headers": auth_manager.config.enable_security_headers,
            "csp": auth_manager.config.enable_content_security_policy
        }
    } 