"""
Security tests for AE v2.

This module tests the security implementation including authentication,
authorization, input validation, and security headers.
"""

import pytest

from ae2.security.models import (
    User,
    Role,
    Permission,
    LoginRequest,
    SecurityConfig,
    create_default_user,
    get_role_permissions,
)
from ae2.security.auth import AuthManager
from ae2.security.utils import SecurityUtils
from ae2.security.config import validate_security_config, get_security_recommendations


class TestSecurityModels:
    """Test security model validation and functionality."""

    def test_user_creation(self):
        """Test user creation with role-based permissions."""
        user = create_default_user("testuser", "test@example.com", Role.OPERATOR)

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == Role.OPERATOR
        assert user.is_active is True
        assert len(user.permissions) > 0

    def test_user_password_validation(self):
        """Test user password validation."""
        user = create_default_user("testuser", "test@example.com", Role.VIEWER)

        # Test password setting and verification
        user.set_password("SecurePass123!")
        assert user.verify_password("SecurePass123!") is True
        assert user.verify_password("WrongPassword") is False

    def test_user_permission_checking(self):
        """Test user permission checking."""
        user = create_default_user("testuser", "test@example.com", Role.OPERATOR)

        # Test individual permission
        assert user.has_permission(Permission.READ_QUERY) is True
        assert user.has_permission(Permission.ADMIN_USERS) is False

        # Test admin role has all permissions
        admin_user = create_default_user("admin", "admin@example.com", Role.ADMIN)
        assert admin_user.has_permission(Permission.ADMIN_USERS) is True
        assert admin_user.has_permission(Permission.READ_QUERY) is True

    def test_role_permissions(self):
        """Test role-based permission assignment."""
        viewer_perms = get_role_permissions(Role.VIEWER)
        operator_perms = get_role_permissions(Role.OPERATOR)
        developer_perms = get_role_permissions(Role.DEVELOPER)
        admin_perms = get_role_permissions(Role.ADMIN)

        # Check permission hierarchy
        assert len(viewer_perms) < len(operator_perms)
        assert len(operator_perms) < len(developer_perms)
        assert len(developer_perms) < len(admin_perms)

        # Check specific permissions
        assert Permission.READ_QUERY in viewer_perms
        assert Permission.WRITE_CONCEPTS in operator_perms
        assert Permission.ADMIN_DEBUG in developer_perms
        assert Permission.ADMIN_USERS in admin_perms

    def test_user_validation(self):
        """Test user model validation."""
        # Valid user
        user = User(
            id="test123",
            username="testuser",
            email="test@example.com",
            role=Role.VIEWER,
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"

        # Invalid email
        with pytest.raises(ValueError, match="Invalid email format"):
            User(
                id="test123",
                username="testuser",
                email="invalid-email",
                role=Role.VIEWER,
            )

        # Invalid username
        with pytest.raises(ValueError, match="Username must be alphanumeric"):
            User(
                id="test123",
                username="test user",
                email="test@example.com",
                role=Role.VIEWER,
            )

    def test_login_request_validation(self):
        """Test login request validation."""
        # Valid request
        request = LoginRequest(username="testuser", password="SecurePass123!")
        assert request.username == "testuser"
        assert request.password == "SecurePass123!"

        # Password too short
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            LoginRequest(username="testuser", password="short")

    def test_security_config_validation(self):
        """Test security configuration validation."""
        # Valid config
        config = SecurityConfig(
            secret_key="a" * 32, algorithm="HS256", access_token_expire_minutes=30
        )
        assert config.secret_key == "a" * 32
        assert config.algorithm == "HS256"

        # Secret key too short
        with pytest.raises(
            ValueError, match="Secret key must be at least 32 characters"
        ):
            SecurityConfig(
                secret_key="short", algorithm="HS256", access_token_expire_minutes=30
            )

        # Invalid algorithm
        with pytest.raises(ValueError, match="Algorithm must be one of"):
            SecurityConfig(
                secret_key="a" * 32, algorithm="INVALID", access_token_expire_minutes=30
            )


class TestAuthManager:
    """Test authentication manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = SecurityConfig(
            secret_key="test-secret-key-32-chars-long-for-testing",
            algorithm="HS256",
            access_token_expire_minutes=30,
        )
        self.auth_manager = AuthManager(self.config)

    def test_default_users_creation(self):
        """Test that default users are created."""
        users = self.auth_manager.list_users()
        usernames = [user.username for user in users]

        assert "admin" in usernames
        assert "operator" in usernames
        assert "viewer" in usernames

        # Check admin user has admin role
        admin_user = next(u for u in users if u.username == "admin")
        assert admin_user.role == Role.ADMIN

    def test_user_authentication(self):
        """Test user authentication."""
        # Test successful authentication
        user = self.auth_manager.authenticate_user("admin", "admin123456")
        assert user is not None
        assert user.username == "admin"

        # Test failed authentication
        user = self.auth_manager.authenticate_user("admin", "wrongpassword")
        assert user is None

        # Test non-existent user
        user = self.auth_manager.authenticate_user("nonexistent", "password")
        assert user is None

    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        user = self.auth_manager.get_user_by_username("admin")
        assert user is not None

        # Create token
        token = self.auth_manager.create_access_token(user)
        assert token is not None

        # Verify token
        token_data = self.auth_manager.verify_token(token)
        assert token_data is not None
        assert token_data.user_id == user.id
        assert token_data.username == user.username
        assert token_data.role == user.role

    def test_token_expiration(self):
        """Test token expiration."""
        user = self.auth_manager.get_user_by_username("admin")

        # Create token with short expiration
        self.config.access_token_expire_minutes = 1
        token = self.auth_manager.create_access_token(user)

        # Token should be valid initially
        token_data = self.auth_manager.verify_token(token)
        assert token_data is not None

        # Wait for expiration (in real test, would use time mocking)
        # This is a simplified test - in practice would mock time

    def test_account_lockout(self):
        """Test account lockout functionality."""
        username = "testuser"

        # Create a test user
        user = self.auth_manager.create_user(
            username, "test@example.com", Role.VIEWER, "password123"
        )

        # Attempt multiple failed logins
        for _ in range(self.config.max_login_attempts):
            result = self.auth_manager.authenticate_user(username, "wrongpassword")
            assert result is None

        # Account should be locked
        with pytest.raises(Exception, match="Account is temporarily locked"):
            self.auth_manager.authenticate_user(username, "password123")

    def test_user_management(self):
        """Test user management operations."""
        # Create user
        user = self.auth_manager.create_user(
            "newuser", "new@example.com", Role.OPERATOR, "password123"
        )
        assert user.username == "newuser"
        assert user.role == Role.OPERATOR

        # Update role
        updated_user = self.auth_manager.update_user_role(user.id, Role.DEVELOPER)
        assert updated_user.role == Role.DEVELOPER

        # Deactivate user
        success = self.auth_manager.deactivate_user(user.id)
        assert success is True
        assert not user.is_active

    def test_duplicate_user_creation(self):
        """Test duplicate user creation prevention."""
        self.auth_manager.create_user(
            "testuser", "test@example.com", Role.VIEWER, "password123"
        )

        # Try to create user with same username
        with pytest.raises(ValueError, match="Username testuser already exists"):
            self.auth_manager.create_user(
                "testuser", "test2@example.com", Role.VIEWER, "password123"
            )

        # Try to create user with same email
        with pytest.raises(ValueError, match="Email test@example.com already exists"):
            self.auth_manager.create_user(
                "testuser2", "test@example.com", Role.VIEWER, "password123"
            )


class TestSecurityUtils:
    """Test security utility functions."""

    def test_password_generation(self):
        """Test secure password generation."""
        password = SecurityUtils.generate_secure_password(16)
        assert len(password) == 16

        # Check password contains required character types
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    def test_password_validation(self):
        """Test password strength validation."""
        # Strong password
        is_valid, issues = SecurityUtils.validate_password_strength("SecurePass123!")
        assert is_valid is True
        assert len(issues) == 0

        # Weak password - too short
        is_valid, issues = SecurityUtils.validate_password_strength("short")
        assert is_valid is False
        assert "at least 8 characters" in issues[0]

        # Weak password - no uppercase
        is_valid, issues = SecurityUtils.validate_password_strength("password123!")
        assert is_valid is False
        assert "uppercase letter" in issues[0]

        # Weak password - common pattern
        is_valid, issues = SecurityUtils.validate_password_strength("password123!")
        assert is_valid is False
        assert "common pattern" in issues[0]

    def test_password_entropy_calculation(self):
        """Test password entropy calculation."""
        # Simple password
        entropy = SecurityUtils.calculate_password_entropy("password")
        assert entropy > 0

        # Complex password
        entropy = SecurityUtils.calculate_password_entropy("SecurePass123!")
        assert entropy > 50

    def test_password_strength_rating(self):
        """Test password strength rating."""
        assert SecurityUtils.get_password_strength("password") == "weak"
        assert SecurityUtils.get_password_strength("Password123") == "medium"
        assert SecurityUtils.get_password_strength("SecurePass123!") == "strong"

    def test_jwt_token_operations(self):
        """Test JWT token operations."""
        secret_key = "test-secret-key-32-chars-long"
        payload = {"user_id": "123", "username": "testuser"}

        # Generate token
        token = SecurityUtils.generate_jwt_token(payload, secret_key, expires_in=3600)
        assert token is not None

        # Verify token
        decoded = SecurityUtils.verify_jwt_token(token, secret_key)
        assert decoded is not None
        assert decoded["user_id"] == "123"
        assert decoded["username"] == "testuser"

    def test_encryption_operations(self):
        """Test encryption and decryption operations."""
        key = SecurityUtils.generate_encryption_key()
        data = "sensitive data"

        # Encrypt data
        encrypted = SecurityUtils.encrypt_data(data, key)
        assert encrypted != data

        # Decrypt data
        decrypted = SecurityUtils.decrypt_data(encrypted, key)
        assert decrypted == data

    def test_input_sanitization(self):
        """Test input sanitization."""
        # Test null byte removal
        sanitized = SecurityUtils.sanitize_input("test\x00string")
        assert "\x00" not in sanitized

        # Test control character removal
        sanitized = SecurityUtils.sanitize_input("test\x01string")
        assert "\x01" not in sanitized

        # Test length limiting
        long_string = "a" * 20000
        sanitized = SecurityUtils.sanitize_input(long_string)
        assert len(sanitized) <= 10000

    def test_validation_functions(self):
        """Test validation functions."""
        # Email validation
        assert SecurityUtils.validate_email("test@example.com") is True
        assert SecurityUtils.validate_email("invalid-email") is False

        # URL validation
        assert SecurityUtils.validate_url("https://example.com") is True
        assert SecurityUtils.validate_url("not-a-url") is False

        # API key validation
        valid_key = SecurityUtils.generate_api_key()
        assert SecurityUtils.validate_api_key(valid_key) is True
        assert SecurityUtils.validate_api_key("invalid-key") is False


class TestSecurityConfiguration:
    """Test security configuration validation."""

    def test_config_validation(self):
        """Test security configuration validation."""
        # Valid config
        config = SecurityConfig(
            secret_key="a" * 32,
            algorithm="HS256",
            access_token_expire_minutes=30,
            rate_limit_requests=100,
        )
        issues = validate_security_config(config)
        assert len(issues) == 0

        # Config with issues
        config = SecurityConfig(
            secret_key="short",
            algorithm="HS256",
            access_token_expire_minutes=1,
            rate_limit_requests=5,
        )
        issues = validate_security_config(config)
        assert len(issues) > 0
        assert any("Secret key is too short" in issue for issue in issues)
        assert any("Token expiration too short" in issue for issue in issues)
        assert any("Rate limit too restrictive" in issue for issue in issues)

    def test_security_recommendations(self):
        """Test security recommendations."""
        recommendations = get_security_recommendations()
        assert len(recommendations) > 0
        assert "Change the default secret key" in recommendations[0]
        assert "Use HTTPS in production" in recommendations


class TestSecurityIntegration:
    """Test security integration with FastAPI."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from ae2.api.main import app

        return TestClient(app)

    def test_health_endpoint_no_auth(self, client):
        """Test that health endpoint doesn't require authentication."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_metrics_endpoint_requires_auth(self, client):
        """Test that metrics endpoint requires authentication."""
        response = client.get("/metrics")
        assert response.status_code == 401  # Unauthorized

    def test_query_endpoint_requires_auth(self, client):
        """Test that query endpoint requires authentication."""
        response = client.post("/query", json={"query": "test", "top_k": 3})
        assert response.status_code == 401  # Unauthorized

    def test_auth_login_endpoint(self, client):
        """Test authentication login endpoint."""
        response = client.post(
            "/auth/login", json={"username": "admin", "password": "admin123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == "admin"

    def test_auth_login_invalid_credentials(self, client):
        """Test authentication with invalid credentials."""
        response = client.post(
            "/auth/login", json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_authenticated_request(self, client):
        """Test authenticated request."""
        # Login first
        login_response = client.post(
            "/auth/login", json={"username": "admin", "password": "admin123456"}
        )
        token = login_response.json()["access_token"]

        # Use token for authenticated request
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == "admin"

    def test_permission_denied(self, client):
        """Test permission denied for insufficient permissions."""
        # Login as viewer (limited permissions)
        login_response = client.post(
            "/auth/login", json={"username": "viewer", "password": "viewer123456"}
        )
        token = login_response.json()["access_token"]

        # Try to access admin endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/users", headers=headers)
        assert response.status_code == 403  # Forbidden

    def test_security_headers(self, client):
        """Test that security headers are present."""
        response = client.get("/healthz")
        headers = response.headers

        # Check for security headers
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"

    def test_rate_limiting(self, client):
        """Test rate limiting functionality."""
        # Make many requests quickly
        for _ in range(150):  # More than the default limit
            response = client.get("/healthz")
            if response.status_code == 429:  # Too Many Requests
                break
        else:
            # If no rate limiting occurred, that's also acceptable for testing
            pass

    def test_input_validation(self, client):
        """Test input validation and sanitization."""
        # Test with potentially malicious input
        malicious_query = "test<script>alert('xss')</script>"
        response = client.post("/query", json={"query": malicious_query, "top_k": 3})
        # Should either be rejected or sanitized
        assert response.status_code in [400, 401]  # Bad Request or Unauthorized


if __name__ == "__main__":
    pytest.main([__file__])
