# enterprise/federation/multi_tenant.py
import jwt
import bcrypt
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging
from functools import wraps
import hashlib
import secrets

Base = declarative_base()

@dataclass
class SecurityConfig:
    """Security configuration for multi-tenant BCI system"""
    jwt_secret: str
    jwt_expiration_hours: int = 24
    password_min_length: int = 12
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    encryption_key: str = None
    require_mfa: bool = True
    session_timeout_minutes: int = 60

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    permissions = Column(Text)  # JSON string of permissions
    created_at = Column(DateTime, default=datetime.utcnow)

class UserRole(Base):
    __tablename__ = 'user_roles'
    
    user_id = Column(String, primary_key=True)
    role_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    granted_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    jwt_token = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

class TenantSecurityManager:
    """Multi-tenant security manager for BCI enterprise systems"""
    
    def __init__(self, config: SecurityConfig, database_url: str):
        self.config = config
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        # Initialize encryption
        if config.encryption_key:
            self.cipher = Fernet(config.encryption_key.encode())
        else:
            self.cipher = Fernet(Fernet.generate_key())
        
        # Default permissions for different user types
        self.default_permissions = {
            'admin': [
                'user.create', 'user.read', 'user.update', 'user.delete',
                'neural_data.read', 'neural_data.write', 'neural_data.delete',
                'model.create', 'model.read', 'model.update', 'model.delete',
                'system.admin', 'billing.read'
            ],
            'researcher': [
                'neural_data.read', 'neural_data.write',
                'model.create', 'model.read', 'model.update',
                'analysis.run', 'export.data'
            ],
            'clinician': [
                'neural_data.read', 'patient.read', 'patient.write',
                'model.read', 'analysis.run', 'report.generate'
            ],
            'viewer': [
                'neural_data.read', 'model.read', 'analysis.read'
            ]
        }
    
    def get_db(self) -> Session:
        """Get database session"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create_tenant_user(self, tenant_id: str, username: str, email: str, 
                          password: str, role: str = 'researcher') -> Dict[str, Any]:
        """Create a new user in a specific tenant"""
        with self.SessionLocal() as db:
            # Check if user already exists
            existing_user = db.query(User).filter(
                User.username == username,
                User.tenant_id == tenant_id
            ).first()
            
            if existing_user:
                raise ValueError(f"User {username} already exists in tenant {tenant_id}")
            
            # Validate password strength
            if not self._validate_password_strength(password):
                raise ValueError("Password does not meet security requirements")
            
            # Generate salt and hash password
            salt = secrets.token_hex(16)
            password_hash = bcrypt.hashpw(
                (password + salt).encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Create user
            user = User(
                id=secrets.token_urlsafe(16),
                tenant_id=tenant_id,
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                mfa_enabled=self.config.require_mfa
            )
            
            db.add(user)
            db.commit()
            
            # Assign default role
            self._assign_role(db, user.id, tenant_id, role)
            
            return {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'tenant_id': user.tenant_id,
                'created_at': user.created_at
            }
    
    def authenticate_user(self, tenant_id: str, username: str, password: str, 
                         mfa_token: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate user with multi-factor authentication"""
        with self.SessionLocal() as db:
            user = db.query(User).filter(
                User.username == username,
                User.tenant_id == tenant_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise ValueError("Invalid username or password")
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                raise ValueError("Account is locked due to failed login attempts")
            
            # Verify password
            if not bcrypt.checkpw(
                (password + user.salt).encode('utf-8'),
                user.password_hash.encode('utf-8')
            ):
                # Increment failed attempts
                user.failed_attempts += 1
                if user.failed_attempts >= self.config.max_failed_attempts:
                    user.locked_until = datetime.utcnow() + timedelta(
                        minutes=self.config.lockout_duration_minutes
                    )
                db.commit()
                raise ValueError("Invalid username or password")
            
            # Verify MFA if enabled
            if user.mfa_enabled and not self._verify_mfa_token(user.mfa_secret, mfa_token):
                raise ValueError("Invalid MFA token")
            
            # Reset failed attempts on successful login
            user.failed_attempts = 0
            user.locked_until = None
            user.last_login = datetime.utcnow()
            db.commit()
            
            # Generate JWT token
            jwt_token = self._generate_jwt_token(user.id, tenant_id)
            
            # Create session
            session = Session(
                id=secrets.token_urlsafe(32),
                user_id=user.id,
                tenant_id=tenant_id,
                jwt_token=jwt_token,
                expires_at=datetime.utcnow() + timedelta(hours=self.config.jwt_expiration_hours)
            )
            
            db.add(session)
            db.commit()
            
            return {
                'user_id': user.id,
                'username': user.username,
                'tenant_id': user.tenant_id,
                'jwt_token': jwt_token,
                'session_id': session.id,
                'expires_at': session.expires_at
            }
    
    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return user information"""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=['HS256']
            )
            
            # Check session validity
            with self.SessionLocal() as db:
                session = db.query(Session).filter(
                    Session.jwt_token == token,
                    Session.is_active == True,
                    Session.expires_at > datetime.utcnow()
                ).first()
                
                if not session:
                    raise ValueError("Invalid or expired session")
                
                return {
                    'user_id': payload['user_id'],
                    'tenant_id': payload['tenant_id'],
                    'permissions': payload.get('permissions', []),
                    'session_id': session.id
                }
                
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def check_permission(self, user_id: str, tenant_id: str, permission: str) -> bool:
        """Check if user has specific permission"""
        with self.SessionLocal() as db:
            # Get user roles
            user_roles = db.query(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id
            ).all()
            
            # Check permissions for each role
            for user_role in user_roles:
                role = db.query(Role).filter(Role.id == user_role.role_id).first()
                if role:
                    import json
                    permissions = json.loads(role.permissions)
                    if permission in permissions:
                        return True
            
            return False
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data for storage"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def _validate_password_strength(self, password: str) -> bool:
        """Validate password meets security requirements"""
        if len(password) < self.config.password_min_length:
            return False
        
        # Check for uppercase, lowercase, digit, and special character
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    def _generate_jwt_token(self, user_id: str, tenant_id: str) -> str:
        """Generate JWT token for user"""
        # Get user permissions
        permissions = self._get_user_permissions(user_id, tenant_id)
        
        payload = {
            'user_id': user_id,
            'tenant_id': tenant_id,
            'permissions': permissions,
            'exp': datetime.utcnow() + timedelta(hours=self.config.jwt_expiration_hours),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.config.jwt_secret, algorithm='HS256')
    
    def _get_user_permissions(self, user_id: str, tenant_id: str) -> List[str]:
        """Get all permissions for a user"""
        with self.SessionLocal() as db:
            user_roles = db.query(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id
            ).all()
            
            permissions = set()
            for user_role in user_roles:
                role = db.query(Role).filter(Role.id == user_role.role_id).first()
                if role:
                    import json
                    role_permissions = json.loads(role.permissions)
                    permissions.update(role_permissions)
            
            return list(permissions)
    
    def _assign_role(self, db: Session, user_id: str, tenant_id: str, role_name: str):
        """Assign role to user"""
        # Create role if it doesn't exist
        role = db.query(Role).filter(
            Role.name == role_name,
            Role.tenant_id == tenant_id
        ).first()
        
        if not role:
            role = Role(
                id=secrets.token_urlsafe(16),
                tenant_id=tenant_id,
                name=role_name,
                permissions=json.dumps(self.default_permissions.get(role_name, []))
            )
            db.add(role)
            db.commit()
        
        # Assign role to user
        user_role = UserRole(
            user_id=user_id,
            role_id=role.id,
            tenant_id=tenant_id
        )
        db.add(user_role)
        db.commit()
    
    def _verify_mfa_token(self, secret: str, token: str) -> bool:
        """Verify MFA token (simplified - in production use proper TOTP)"""
        # This is a simplified implementation
        # In production, use libraries like pyotp for proper TOTP verification
        if not token or not secret:
            return False
        
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)

# Decorator for protecting endpoints
def require_permission(permission: str):
    """Decorator to require specific permission for endpoint access"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract JWT token from request headers
            # This would be implemented based on your web framework
            # For example, with FastAPI:
            # authorization: str = Depends(get_authorization_header)
            
            # Validate token and check permission
            # security_manager.validate_jwt_token(token)
            # security_manager.check_permission(user_id, tenant_id, permission)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage example
if __name__ == "__main__":
    config = SecurityConfig(
        jwt_secret="your-secret-key-here",
        jwt_expiration_hours=24,
        require_mfa=True
    )
    
    security_manager = TenantSecurityManager(
        config=config,
        database_url="postgresql://user:password@localhost/neurOS"
    )
    
    # Create tenant user
    user = security_manager.create_tenant_user(
        tenant_id="hospital_001",
        username="researcher_001",
        email="researcher@hospital.com",
        password="SecurePassword123!",
        role="researcher"
    )
    
    print(f"Created user: {user}")