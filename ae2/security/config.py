"""
Security configuration for AE v2.

This module manages security settings and environment variables.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings

from .models import SecurityConfig


class SecuritySettings(BaseSettings):
    """Security settings with environment variable support."""
    
    # JWT Configuration
    secret_key: str = Field(
        default="your-super-secret-key-change-in-production-32-chars-min",
        description="JWT secret key for token signing"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    # Password Policy
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_uppercase: bool = Field(default=True, description="Require uppercase letters")
    password_require_lowercase: bool = Field(default=True, description="Require lowercase letters")
    password_require_digits: bool = Field(default=True, description="Require digits")
    password_require_special: bool = Field(default=True, description="Require special characters")
    
    # Account Security
    max_login_attempts: int = Field(default=5, description="Maximum login attempts")
    lockout_duration_minutes: int = Field(default=15, description="Account lockout duration")
    session_timeout_minutes: int = Field(default=30, description="Session timeout")
    
    # Rate Limiting
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    rate_limit_window_minutes: int = Field(default=1, description="Rate limit window")
    
    # CORS Configuration
    enable_cors: bool = Field(default=True, description="Enable CORS")
    allowed_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    allowed_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    allowed_headers: List[str] = Field(
        default=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
        description="Allowed HTTP headers"
    )
    
    # Security Headers
    enable_security_headers: bool = Field(default=True, description="Enable security headers")
    enable_content_security_policy: bool = Field(default=True, description="Enable CSP")
    enable_hsts: bool = Field(default=True, description="Enable HSTS")
    hsts_max_age: int = Field(default=31536000, description="HSTS max age in seconds")
    
    # Input Validation
    max_content_length: int = Field(default=10485760, description="Maximum content length (10MB)")
    enable_input_validation: bool = Field(default=True, description="Enable input validation")
    enable_xss_protection: bool = Field(default=True, description="Enable XSS protection")
    
    # Audit and Logging
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    audit_log_level: str = Field(default="WARNING", description="Audit log level")
    log_security_events: bool = Field(default=True, description="Log security events")
    
    # File Security
    allowed_file_extensions: List[str] = Field(
        default=[".json", ".txt", ".md", ".yaml", ".yml"],
        description="Allowed file extensions for uploads"
    )
    max_file_size: int = Field(default=5242880, description="Maximum file size (5MB)")
    
    # Network Security
    enable_ip_whitelist: bool = Field(default=False, description="Enable IP whitelist")
    allowed_ips: List[str] = Field(default=[], description="Allowed IP addresses")
    enable_proxy_headers: bool = Field(default=True, description="Enable proxy header processing")
    
    # Encryption
    enable_encryption: bool = Field(default=True, description="Enable data encryption")
    encryption_algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm")
    
    @validator("secret_key")
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v
    
    @validator("algorithm")
    def validate_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(f"Algorithm must be one of: {allowed_algorithms}")
        return v
    
    @validator("password_min_length")
    def validate_password_min_length(cls, v: int) -> int:
        """Validate minimum password length."""
        if v < 8:
            raise ValueError("Minimum password length must be at least 8")
        return v
    
    @validator("max_login_attempts")
    def validate_max_login_attempts(cls, v: int) -> int:
        """Validate maximum login attempts."""
        if v < 1 or v > 20:
            raise ValueError("Maximum login attempts must be between 1 and 20")
        return v
    
    @validator("rate_limit_requests")
    def validate_rate_limit_requests(cls, v: int) -> int:
        """Validate rate limit requests."""
        if v < 1 or v > 10000:
            raise ValueError("Rate limit requests must be between 1 and 10000")
        return v
    
    @validator("allowed_origins")
    def validate_allowed_origins(cls, v: List[str]) -> List[str]:
        """Validate allowed origins."""
        if not v:
            raise ValueError("At least one origin must be allowed")
        return v
    
    def to_security_config(self) -> SecurityConfig:
        """Convert to SecurityConfig model."""
        return SecurityConfig(
            secret_key=self.secret_key,
            algorithm=self.algorithm,
            access_token_expire_minutes=self.access_token_expire_minutes,
            refresh_token_expire_days=self.refresh_token_expire_days,
            password_min_length=self.password_min_length,
            max_login_attempts=self.max_login_attempts,
            lockout_duration_minutes=self.lockout_duration_minutes,
            enable_rate_limiting=self.enable_rate_limiting,
            rate_limit_requests=self.rate_limit_requests,
            enable_cors=self.enable_cors,
            allowed_origins=self.allowed_origins,
            enable_security_headers=self.enable_security_headers,
            enable_content_security_policy=self.enable_content_security_policy
        )
    
    class Config:
        env_prefix = "AE_SECURITY_"
        env_file = ".env"
        case_sensitive = False


def get_security_settings() -> SecuritySettings:
    """Get security settings from environment."""
    return SecuritySettings()


def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    settings = get_security_settings()
    return settings.to_security_config()


# Environment variable mapping
ENV_VAR_MAPPING = {
    "AE_SECRET_KEY": "secret_key",
    "AE_JWT_ALGORITHM": "algorithm",
    "AE_TOKEN_EXPIRE_MINUTES": "access_token_expire_minutes",
    "AE_RATE_LIMITING": "enable_rate_limiting",
    "AE_RATE_LIMIT_REQUESTS": "rate_limit_requests",
    "AE_ENABLE_CORS": "enable_cors",
    "AE_SECURITY_HEADERS": "enable_security_headers",
    "AE_CSP": "enable_content_security_policy",
    "AE_MAX_LOGIN_ATTEMPTS": "max_login_attempts",
    "AE_LOCKOUT_DURATION": "lockout_duration_minutes",
    "AE_PASSWORD_MIN_LENGTH": "password_min_length",
}


def load_security_config_from_env() -> SecurityConfig:
    """Load security configuration from environment variables."""
    config_dict = {}
    
    for env_var, config_key in ENV_VAR_MAPPING.items():
        value = os.getenv(env_var)
        if value is not None:
            # Convert string values to appropriate types
            if config_key in ["access_token_expire_minutes", "refresh_token_expire_days", 
                             "password_min_length", "max_login_attempts", 
                             "lockout_duration_minutes", "rate_limit_requests"]:
                config_dict[config_key] = int(value)
            elif config_key in ["enable_rate_limiting", "enable_cors", 
                               "enable_security_headers", "enable_content_security_policy"]:
                config_dict[config_key] = value.lower() in ("true", "1", "yes")
            else:
                config_dict[config_key] = value
    
    # Set defaults for required fields
    if "secret_key" not in config_dict:
        config_dict["secret_key"] = "your-super-secret-key-change-in-production-32-chars-min"
    
    return SecurityConfig(**config_dict)


def validate_security_config(config: SecurityConfig) -> List[str]:
    """Validate security configuration and return issues."""
    issues = []
    
    # Check secret key strength
    if len(config.secret_key) < 32:
        issues.append("Secret key is too short (minimum 32 characters)")
    
    # Check for default secret key
    if config.secret_key == "your-super-secret-key-change-in-production-32-chars-min":
        issues.append("Using default secret key - change in production")
    
    # Check token expiration
    if config.access_token_expire_minutes < 5:
        issues.append("Token expiration too short (minimum 5 minutes)")
    elif config.access_token_expire_minutes > 1440:
        issues.append("Token expiration too long (maximum 24 hours)")
    
    # Check rate limiting
    if config.rate_limit_requests < 10:
        issues.append("Rate limit too restrictive (minimum 10 requests per minute)")
    elif config.rate_limit_requests > 10000:
        issues.append("Rate limit too permissive (maximum 10000 requests per minute)")
    
    # Check password policy
    if config.password_min_length < 8:
        issues.append("Password minimum length too short (minimum 8 characters)")
    
    # Check lockout settings
    if config.max_login_attempts < 3:
        issues.append("Maximum login attempts too low (minimum 3)")
    elif config.max_login_attempts > 20:
        issues.append("Maximum login attempts too high (maximum 20)")
    
    if config.lockout_duration_minutes < 5:
        issues.append("Lockout duration too short (minimum 5 minutes)")
    elif config.lockout_duration_minutes > 1440:
        issues.append("Lockout duration too long (maximum 24 hours)")
    
    return issues


def get_security_recommendations() -> List[str]:
    """Get security recommendations for production deployment."""
    return [
        "Change the default secret key to a strong, random value",
        "Use HTTPS in production",
        "Set appropriate CORS origins instead of '*'",
        "Enable rate limiting",
        "Enable security headers",
        "Enable Content Security Policy",
        "Use strong password policies",
        "Implement proper logging and monitoring",
        "Regularly rotate secrets and keys",
        "Keep dependencies updated",
        "Use environment variables for sensitive configuration",
        "Implement proper error handling without information disclosure",
        "Consider using a reverse proxy for additional security",
        "Implement proper session management",
        "Use secure cookie settings",
        "Consider implementing 2FA for admin accounts",
        "Regular security audits and penetration testing",
        "Backup and disaster recovery procedures",
        "Monitor for suspicious activities",
        "Implement proper access controls"
    ] 