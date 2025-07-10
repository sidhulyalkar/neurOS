# neuros/enterprise/security.py
"""
Enterprise Security Module for neurOS
Handles authentication, authorization, data encryption, and compliance
"""

import hashlib
import hmac
import jwt
import secrets
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import json

class SecurityLevel(Enum):
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"

class UserRole(Enum):
    VIEWER = "viewer"
    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(Enum):
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    DELETE_DATA = "delete_data"
    MANAGE_PIPELINES = "manage_pipelines"
    MANAGE_DEVICES = "manage_devices"
    MANAGE_USERS = "manage_users"
    SYSTEM_ADMIN = "system_admin"
    EXPORT_DATA = "export_data"
    REAL_TIME_ACCESS = "real_time_access"

@dataclass
class User:
    """User account information"""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked: bool = False
    password_hash: Optional[str] = None
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None

@dataclass
class SecurityConfig:
    """Security configuration"""
    level: SecurityLevel = SecurityLevel.STANDARD
    jwt_secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_expiry_hours: int = 24
    password_min_length: int = 12
    password_require_complexity: bool = True
    max_failed_login_attempts: int = 5
    account_lockout_duration_minutes: int = 30
    mfa_required: bool = False
    data_encryption_enabled: bool = True
    audit_logging_enabled: bool = True
    session_timeout_minutes: int = 60

class PasswordManager:
    """Secure password handling"""
    
    @staticmethod
    def hash_password(password: str, salt: bytes = None) -> tuple[str, bytes]:
        """Hash password with salt"""
        if salt is None:
            salt = os.urandom(32)
        
        pwdhash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # 100k iterations
        )
        
        return base64.b64encode(pwdhash).decode('ascii'), salt
    
    @staticmethod
    def verify_password(password: str, hash_str: str, salt: bytes) -> bool:
        """Verify password against hash"""
        pwdhash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        
        return base64.b64encode(pwdhash).decode('ascii') == hash_str
    
    @staticmethod
    def validate_password_strength(password: str, config: SecurityConfig) -> tuple[bool, List[str]]:
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < config.password_min_length:
            errors.append(f"Password must be at least {config.password_min_length} characters")
        
        if config.password_require_complexity:
            if not any(c.isupper() for c in password):
                errors.append("Password must contain uppercase letters")
            if not any(c.islower() for c in password):
                errors.append("Password must contain lowercase letters")
            if not any(c.isdigit() for c in password):
                errors.append("Password must contain numbers")
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                errors.append("Password must contain special characters")
        
        return len(errors) == 0, errors

class DataEncryption:
    """Data encryption/decryption utilities"""
    
    def __init__(self, encryption_key: bytes = None):
        if encryption_key is None:
            encryption_key = Fernet.generate_key()
        elif isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.fernet = Fernet(encryption_key)
        self.key = encryption_key
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt string data"""
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.fernet.encrypt(data)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary as JSON"""
        json_str = json.dumps(data)
        return self.encrypt_data(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary from JSON"""
        json_str = self.decrypt_data(encrypted_data)
        return json.loads(json_str)
    
    @staticmethod
    def generate_key_from_password(password: str, salt: bytes = None) -> bytes:
        """Generate encryption key from password"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

class MFAManager:
    """Multi-factor authentication management"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate MFA secret key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_totp_token(secret: str, window: int = 30) -> str:
        """Generate TOTP token (simplified implementation)"""
        import time
        import struct
        
        # Current time window
        time_window = int(time.time()) // window
        
        # Convert to bytes
        secret_bytes = base64.b32decode(secret.upper() + '=' * (-len(secret) % 8))
        time_bytes = struct.pack('>Q', time_window)
        
        # Generate HMAC
        hmac_digest = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()
        
        # Extract 6-digit code
        offset = hmac_digest[-1] & 0x0f
        code = struct.unpack('>I', hmac_digest[offset:offset+4])[0] & 0x7fffffff
        
        return f"{code % 1000000:06d}"
    
    @staticmethod
    def verify_totp_token(secret: str, token: str, window: int = 30, tolerance: int = 1) -> bool:
        """Verify TOTP token with time tolerance"""
        import time
        
        current_window = int(time.time()) // window
        
        # Check current window and adjacent windows
        for w in range(current_window - tolerance, current_window + tolerance + 1):
            expected_token = MFAManager.generate_totp_token(secret, window)
            if hmac.compare_digest(token, expected_token):
                return True
        
        return False

class AuditLogger:
    """Security audit logging"""
    
    def __init__(self, log_file: str = "neuros_audit.log"):
        self.logger = logging.getLogger("neurOS.security.audit")
        
        # Configure file handler for audit logs
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_login_attempt(self, username: str, success: bool, ip_address: str = None):
        """Log login attempt"""
        status = "SUCCESS" if success else "FAILED"
        message = f"LOGIN_{status} - User: {username}"
        if ip_address:
            message += f" - IP: {ip_address}"
        
        self.logger.info(message)
    
    def log_data_access(self, user_id: str, resource: str, action: str):
        """Log data access event"""
        message = f"DATA_ACCESS - User: {user_id} - Resource: {resource} - Action: {action}"
        self.logger.info(message)
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log general security event"""
        message = f"SECURITY_EVENT - Type: {event_type} - Details: {json.dumps(details)}"
        self.logger.warning(message)
    
    def log_admin_action(self, admin_user: str, action: str, target: str = None):
        """Log administrative action"""
        message = f"ADMIN_ACTION - Admin: {admin_user} - Action: {action}"
        if target:
            message += f" - Target: {target}"
        self.logger.info(message)

class AuthenticationManager:
    """Handles user authentication and session management"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.users: Dict[str, User] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.encryption = DataEncryption()
        self.audit_logger = AuditLogger()
        self.mfa_manager = MFAManager()
        
        # Load default admin user
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user"""
        admin_user = User(
            user_id="admin",
            username="admin",
            email="admin@neuros.local",
            role=UserRole.SUPER_ADMIN,
            permissions=set(Permission)  # All permissions
        )
        
        # Set default password (should be changed on first login)
        password_hash, salt = PasswordManager.hash_password("neurOS_admin_2024!")
        admin_user.password_hash = password_hash
        
        self.users["admin"] = admin_user
    
    def create_user(self, username: str, email: str, password: str, 
                   role: UserRole, permissions: Set[Permission] = None) -> tuple[bool, str]:
        """Create new user account"""
        # Validate password
        valid, errors = PasswordManager.validate_password_strength(password, self.config)
        if not valid:
            return False, "; ".join(errors)
        
        # Check if user exists
        if any(u.username == username for u in self.users.values()):
            return False, "Username already exists"
        
        # Create user
        user_id = secrets.token_urlsafe(16)
        password_hash, salt = PasswordManager.hash_password(password)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=permissions or set(),
            password_hash=password_hash
        )
        
        self.users[user_id] = user
        self.audit_logger.log_admin_action("system", "USER_CREATED", username)
        
        return True, "User created successfully"
    
    def authenticate_user(self, username: str, password: str, 
                         mfa_token: str = None, ip_address: str = None) -> tuple[bool, str, Optional[str]]:
        """Authenticate user login"""
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break
        
        if not user:
            self.audit_logger.log_login_attempt(username, False, ip_address)
            return False, "Invalid credentials", None
        
        # Check account lock
        if user.account_locked:
            self.audit_logger.log_login_attempt(username, False, ip_address)
            return False, "Account locked", None
        
        # Verify password
        if not PasswordManager.verify_password(password, user.password_hash, b""):  # Simplified
            user.failed_login_attempts += 1
            
            if user.failed_login_attempts >= self.config.max_failed_login_attempts:
                user.account_locked = True
                self.audit_logger.log_security_event("ACCOUNT_LOCKED", {
                    "username": username,
                    "failed_attempts": user.failed_login_attempts
                })
            
            self.audit_logger.log_login_attempt(username, False, ip_address)
            return False, "Invalid credentials", None
        
        # Check MFA if enabled
        if user.mfa_enabled or self.config.mfa_required:
            if not mfa_token:
                return False, "MFA token required", None
            
            if not self.mfa_manager.verify_totp_token(user.mfa_secret or "", mfa_token):
                self.audit_logger.log_login_attempt(username, False, ip_address)
                return False, "Invalid MFA token", None
        
        # Generate session token
        session_token = self._create_session(user)
        
        # Reset failed attempts
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        
        self.audit_logger.log_login_attempt(username, True, ip_address)
        
        return True, "Authentication successful", session_token
    
    def _create_session(self, user: User) -> str:
        """Create user session with JWT token"""
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'role': user.role.value,
            'permissions': [p.value for p in user.permissions],
            'exp': datetime.utcnow() + timedelta(hours=self.config.jwt_expiry_hours),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.config.jwt_secret, algorithm='HS256')
        
        # Store session info
        self.active_sessions[token] = {
            'user_id': user.user_id,
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow()
        }
        
        return token
    
    def validate_session(self, token: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate session token"""
        try:
            payload = jwt.decode(token, self.config.jwt_secret, algorithms=['HS256'])
            
            # Check if session exists and is active
            if token not in self.active_sessions:
                return False, None
            
            session_info = self.active_sessions[token]
            
            # Check session timeout
            if (datetime.utcnow() - session_info['last_activity']).total_seconds() > (self.config.session_timeout_minutes * 60):
                del self.active_sessions[token]
                return False, None
            
            # Update last activity
            session_info['last_activity'] = datetime.utcnow()
            
            return True, payload
            
        except jwt.ExpiredSignatureError:
            if token in self.active_sessions:
                del self.active_sessions[token]
            return False, None
        except jwt.InvalidTokenError:
            return False, None
    
    def logout_user(self, token: str):
        """Logout user by invalidating session"""
        if token in self.active_sessions:
            user_id = self.active_sessions[token]['user_id']
            del self.active_sessions[token]
            
            user = self.users.get(user_id)
            if user:
                self.audit_logger.log_security_event("LOGOUT", {"username": user.username})
    
    def enable_mfa(self, user_id: str) -> tuple[bool, str]:
        """Enable MFA for user"""
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        user.mfa_secret = self.mfa_manager.generate_secret()
        user.mfa_enabled = True
        
        self.audit_logger.log_security_event("MFA_ENABLED", {"user_id": user_id})
        
        return True, user.mfa_secret

class AuthorizationManager:
    """Handles user authorization and permissions"""
    
    def __init__(self):
        self.role_permissions = {
            UserRole.VIEWER: {Permission.READ_DATA},
            UserRole.RESEARCHER: {
                Permission.READ_DATA,
                Permission.WRITE_DATA,
                Permission.MANAGE_PIPELINES,
                Permission.EXPORT_DATA
            },
            UserRole.DEVELOPER: {
                Permission.READ_DATA,
                Permission.WRITE_DATA,
                Permission.MANAGE_PIPELINES,
                Permission.MANAGE_DEVICES,
                Permission.REAL_TIME_ACCESS,
                Permission.EXPORT_DATA
            },
            UserRole.ADMIN: {
                Permission.READ_DATA,
                Permission.WRITE_DATA,
                Permission.DELETE_DATA,
                Permission.MANAGE_PIPELINES,
                Permission.MANAGE_DEVICES,
                Permission.MANAGE_USERS,
                Permission.EXPORT_DATA,
                Permission.REAL_TIME_ACCESS
            },
            UserRole.SUPER_ADMIN: set(Permission)  # All permissions
        }
    
    def check_permission(self, user_role: UserRole, user_permissions: Set[Permission], 
                        required_permission: Permission) -> bool:
        """Check if user has required permission"""
        # Check role-based permissions
        role_perms = self.role_permissions.get(user_role, set())
        if required_permission in role_perms:
            return True
        
        # Check user-specific permissions
        if required_permission in user_permissions:
            return True
        
        return False
    
    def get_user_permissions(self, user_role: UserRole, user_permissions: Set[Permission]) -> Set[Permission]:
        """Get all permissions for user"""
        role_perms = self.role_permissions.get(user_role, set())
        return role_perms.union(user_permissions)

class ComplianceManager:
    """Handles regulatory compliance (HIPAA, GDPR, etc.)"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.audit_logger = AuditLogger()
        self.data_retention_days = 7 * 365  # 7 years default
        self.anonymization_enabled = True
    
    def anonymize_data(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Anonymize sensitive data for compliance"""
        anonymized = data.copy()
        
        # Remove direct identifiers
        sensitive_fields = ['patient_id', 'subject_id', 'name', 'email', 'phone']
        for field in sensitive_fields:
            if field in anonymized:
                anonymized[field] = self._hash_identifier(anonymized[field], user_id)
        
        # Add anonymization timestamp
        anonymized['_anonymized_at'] = datetime.utcnow().isoformat()
        anonymized['_anonymization_method'] = 'neurOS_standard'
        
        self.audit_logger.log_data_access(user_id, "data_anonymization", "ANONYMIZE")
        
        return anonymized
    
    def _hash_identifier(self, identifier: str, salt: str) -> str:
        """Hash identifier for anonymization"""
        return hashlib.sha256(f"{identifier}_{salt}".encode()).hexdigest()[:16]
    
    def check_data_retention(self, data_timestamp: datetime) -> bool:
        """Check if data exceeds retention policy"""
        age_days = (datetime.utcnow() - data_timestamp).days
        return age_days <= self.data_retention_days
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance status report"""
        return {
            'security_level': self.config.level.value,
            'encryption_enabled': self.config.data_encryption_enabled,
            'audit_logging_enabled': self.config.audit_logging_enabled,
            'mfa_required': self.config.mfa_required,
            'data_retention_days': self.data_retention_days,
            'anonymization_enabled': self.anonymization_enabled,
            'report_generated_at': datetime.utcnow().isoformat()
        }

class SecurityManager:
    """Main security manager coordinating all security components"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.auth_manager = AuthenticationManager(self.config)
        self.authz_manager = AuthorizationManager()
        self.compliance_manager = ComplianceManager(self.config)
        self.encryption = DataEncryption()
        self.audit_logger = AuditLogger()
        
        self.logger = logging.getLogger("neurOS.security")
        self.logger.info(f"Security manager initialized with {self.config.level.value} security level")
    
    async def authenticate_request(self, token: str, required_permission: Permission) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Authenticate and authorize a request"""
        # Validate session
        valid, payload = self.auth_manager.validate_session(token)
        if not valid:
            return False, None
        
        # Check authorization
        user_role = UserRole(payload['role'])
        user_permissions = {Permission(p) for p in payload['permissions']}
        
        authorized = self.authz_manager.check_permission(
            user_role, user_permissions, required_permission
        )
        
        if not authorized:
            self.audit_logger.log_security_event("UNAUTHORIZED_ACCESS", {
                "user_id": payload['user_id'],
                "required_permission": required_permission.value
            })
            return False, None
        
        return True, payload
    
    def encrypt_sensitive_data(self, data: Any) -> str:
        """Encrypt sensitive data if encryption is enabled"""
        if not self.config.data_encryption_enabled:
            return data
        
        if isinstance(data, dict):
            return self.encryption.encrypt_dict(data)
        else:
            return self.encryption.encrypt_data(str(data))
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> Any:
        """Decrypt sensitive data"""
        if not self.config.data_encryption_enabled:
            return encrypted_data
        
        try:
            return self.encryption.decrypt_dict(encrypted_data)
        except:
            return self.encryption.decrypt_data(encrypted_data)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get overall security status"""
        return {
            'security_level': self.config.level.value,
            'active_sessions': len(self.auth_manager.active_sessions),
            'total_users': len(self.auth_manager.users),
            'mfa_enabled_users': sum(1 for u in self.auth_manager.users.values() if u.mfa_enabled),
            'locked_accounts': sum(1 for u in self.auth_manager.users.values() if u.account_locked),
            'encryption_enabled': self.config.data_encryption_enabled,
            'audit_logging_enabled': self.config.audit_logging_enabled,
            'compliance_report': self.compliance_manager.generate_compliance_report()
        }

# Example usage and testing
if __name__ == "__main__":
    async def test_security_system():
        # Create security manager with high security
        config = SecurityConfig(
            level=SecurityLevel.HIGH,
            mfa_required=True,
            data_encryption_enabled=True
        )
        
        security_manager = SecurityManager(config)
        
        # Test user creation
        success, message = security_manager.auth_manager.create_user(
            username="test_researcher",
            email="researcher@neuros.local",
            password="SecurePassword123!",
            role=UserRole.RESEARCHER
        )
        
        print(f"User creation: {success} - {message}")
        
        # Test authentication (would fail without MFA)
        success, message, token = security_manager.auth_manager.authenticate_user(
            username="test_researcher",
            password="SecurePassword123!"
        )
        
        print(f"Authentication: {success} - {message}")
        
        # Test permission check
        if token:
            authorized, payload = await security_manager.authenticate_request(
                token, Permission.READ_DATA
            )
            print(f"Authorization for READ_DATA: {authorized}")
        
        # Test data encryption
        sensitive_data = {"patient_id": "12345", "eeg_data": [1, 2, 3, 4, 5]}
        encrypted = security_manager.encrypt_sensitive_data(sensitive_data)
        decrypted = security_manager.decrypt_sensitive_data(encrypted)
        
        print(f"Encryption test: {decrypted == sensitive_data}")
        
        # Get security status
        status = security_manager.get_security_status()
        print(f"Security status: {status}")
    
    # Run test
    import asyncio
    asyncio.run(test_security_system())