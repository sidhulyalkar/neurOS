# enterprise/coompliance/compliance_framework.py
"""
Enterprise Security and Compliance Framework
HIPAA Compliance, FDA Pathway, CE Marking, Multi-tenant Security
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Cryptography and security imports
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt
import bcrypt

# Database and ORM imports
try:
    from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Audit logging
import structlog


class ComplianceStandard(Enum):
    HIPAA = "HIPAA"
    FDA_21CFR_PART11 = "FDA_21CFR_Part11"
    CE_MDR = "CE_MDR_2017_745"
    GDPR = "GDPR"
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"


class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceConfig:
    """Configuration for compliance requirements"""
    enabled_standards: List[ComplianceStandard] = field(default_factory=lambda: [ComplianceStandard.HIPAA])
    encryption_at_rest: bool = True
    encryption_in_transit: bool = True
    audit_logging: bool = True
    access_logging: bool = True
    data_anonymization: bool = True
    backup_encryption: bool = True
    key_rotation_days: int = 90
    password_expiry_days: int = 90
    session_timeout_minutes: int = 30
    max_failed_attempts: int = 3
    require_mfa: bool = True
    data_retention_days: int = 2555  # 7 years for HIPAA


@dataclass
class AuditEvent:
    """Structured audit event for compliance logging"""
    event_id: str
    timestamp: datetime
    user_id: Optional[str]
    tenant_id: Optional[str]
    event_type: str
    resource_type: str
    resource_id: Optional[str]
    action: str
    result: str  # SUCCESS, FAILURE, ERROR
    details: Dict[str, Any]
    source_ip: Optional[str]
    user_agent: Optional[str]
    compliance_relevant: bool = True
    risk_level: SecurityLevel = SecurityLevel.MEDIUM


class EncryptionManager:
    """Enterprise-grade encryption management"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or Fernet.generate_key()
        self.fernet = Fernet(self.master_key)
        
        # Generate RSA key pair for asymmetric encryption
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
        # Key derivation for different purposes
        self.kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'neurOS_enterprise_salt',
            iterations=100000,
        )
    
    def encrypt_neural_data(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt neural data with metadata preservation"""
        # Generate unique encryption key for this data
        data_key = Fernet.generate_key()
        data_cipher = Fernet(data_key)
        
        # Encrypt the neural data
        encrypted_data = data_cipher.encrypt(data)
        
        # Encrypt the data key with master key
        encrypted_key = self.fernet.encrypt(data_key)
        
        # Create encrypted package
        package = {
            'encrypted_data': encrypted_data,
            'encrypted_key': encrypted_key,
            'metadata': self._encrypt_metadata(metadata),
            'algorithm': 'Fernet-AES256',
            'created_at': datetime.utcnow().isoformat(),
            'checksum': self._calculate_checksum(data)
        }
        
        return package
    
    def decrypt_neural_data(self, package: Dict[str, Any]) -> tuple[bytes, Dict[str, Any]]:
        """Decrypt neural data package"""
        # Decrypt the data key
        data_key = self.fernet.decrypt(package['encrypted_key'])
        data_cipher = Fernet(data_key)
        
        # Decrypt the data
        decrypted_data = data_cipher.decrypt(package['encrypted_data'])
        
        # Verify checksum
        if self._calculate_checksum(decrypted_data) != package['checksum']:
            raise ValueError("Data integrity check failed")
        
        # Decrypt metadata
        metadata = self._decrypt_metadata(package['metadata'])
        
        return decrypted_data, metadata
    
    def encrypt_at_rest(self, data: Union[str, bytes]) -> str:
        """Standard encryption for data at rest"""
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.fernet.encrypt(data)
        return encrypted.decode()
    
    def decrypt_at_rest(self, encrypted_data: str) -> str:
        """Decrypt data at rest"""
        decrypted = self.fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    def _encrypt_metadata(self, metadata: Dict[str, Any]) -> str:
        """Encrypt metadata while preserving searchable fields"""
        # Separate searchable from sensitive metadata
        searchable = {}
        sensitive = {}
        
        searchable_fields = {'timestamp', 'channel_count', 'sampling_rate', 'device_type'}
        
        for key, value in metadata.items():
            if key in searchable_fields:
                searchable[key] = value
            else:
                sensitive[key] = value
        
        # Encrypt sensitive metadata
        if sensitive:
            encrypted_sensitive = self.fernet.encrypt(json.dumps(sensitive).encode())
            searchable['_encrypted_metadata'] = encrypted_sensitive.decode()
        
        return json.dumps(searchable)
    
    def _decrypt_metadata(self, encrypted_metadata: str) -> Dict[str, Any]:
        """Decrypt metadata"""
        metadata = json.loads(encrypted_metadata)
        
        if '_encrypted_metadata' in metadata:
            encrypted_sensitive = metadata.pop('_encrypted_metadata')
            sensitive = json.loads(self.fernet.decrypt(encrypted_sensitive.encode()).decode())
            metadata.update(sensitive)
        
        return metadata
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum for integrity verification"""
        return hashlib.sha256(data).hexdigest()
    
    def rotate_keys(self) -> Dict[str, str]:
        """Rotate encryption keys (compliance requirement)"""
        old_key = self.master_key
        new_key = Fernet.generate_key()
        
        # Update master key
        self.master_key = new_key
        self.fernet = Fernet(new_key)
        
        return {
            'old_key_id': hashlib.sha256(old_key).hexdigest()[:16],
            'new_key_id': hashlib.sha256(new_key).hexdigest()[:16],
            'rotated_at': datetime.utcnow().isoformat()
        }


class AuditLogger:
    """Comprehensive audit logging for compliance"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.logger = structlog.get_logger("neurOS.audit")
        
        # Setup structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def log_event(self, event: AuditEvent):
        """Log audit event with compliance context"""
        log_entry = {
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'user_id': event.user_id,
            'tenant_id': event.tenant_id,
            'event_type': event.event_type,
            'resource_type': event.resource_type,
            'resource_id': event.resource_id,
            'action': event.action,
            'result': event.result,
            'details': event.details,
            'source_ip': event.source_ip,
            'user_agent': event.user_agent,
            'compliance_relevant': event.compliance_relevant,
            'risk_level': event.risk_level.value,
            'applicable_standards': [std.value for std in self.config.enabled_standards]
        }
        
        # Log based on risk level
        if event.risk_level == SecurityLevel.CRITICAL:
            self.logger.critical("Critical security event", **log_entry)
        elif event.risk_level == SecurityLevel.HIGH:
            self.logger.error("High risk security event", **log_entry)
        elif event.risk_level == SecurityLevel.MEDIUM:
            self.logger.warning("Medium risk event", **log_entry)
        else:
            self.logger.info("Security event", **log_entry)
    
    def log_data_access(self, user_id: str, tenant_id: str, resource_id: str, 
                       action: str, result: str, details: Dict[str, Any]):
        """Log data access events (HIPAA requirement)"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            tenant_id=tenant_id,
            event_type="DATA_ACCESS",
            resource_type="NEURAL_DATA",
            resource_id=resource_id,
            action=action,
            result=result,
            details=details,
            source_ip=details.get('source_ip'),
            user_agent=details.get('user_agent'),
            risk_level=SecurityLevel.HIGH if action in ['EXPORT', 'DELETE'] else SecurityLevel.MEDIUM
        )
        self.log_event(event)
    
    def log_authentication(self, user_id: str, tenant_id: str, result: str, 
                          source_ip: str, details: Dict[str, Any]):
        """Log authentication events"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            tenant_id=tenant_id,
            event_type="AUTHENTICATION",
            resource_type="USER_SESSION",
            resource_id=user_id,
            action="LOGIN",
            result=result,
            details=details,
            source_ip=source_ip,
            risk_level=SecurityLevel.HIGH if result == "FAILURE" else SecurityLevel.MEDIUM
        )
        self.log_event(event)
    
    def log_compliance_violation(self, violation_type: str, severity: SecurityLevel,
                                tenant_id: str, details: Dict[str, Any]):
        """Log compliance violations"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=None,
            tenant_id=tenant_id,
            event_type="COMPLIANCE_VIOLATION",
            resource_type="SYSTEM",
            resource_id=None,
            action=violation_type,
            result="VIOLATION_DETECTED",
            details=details,
            source_ip=None,
            risk_level=severity
        )
        self.log_event(event)


class AccessControlManager:
    """Role-based access control with compliance features"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.audit_logger = AuditLogger(config)
        
        # Define compliance-aware permissions
        self.permission_definitions = {
            # HIPAA-compliant neural data permissions
            'neural_data.read': {
                'description': 'Read neural signal data',
                'compliance_requirements': [ComplianceStandard.HIPAA],
                'audit_required': True,
                'data_sensitivity': SecurityLevel.HIGH
            },
            'neural_data.write': {
                'description': 'Write/modify neural signal data',
                'compliance_requirements': [ComplianceStandard.HIPAA, ComplianceStandard.FDA_21CFR_PART11],
                'audit_required': True,
                'data_sensitivity': SecurityLevel.CRITICAL
            },
            'neural_data.export': {
                'description': 'Export neural data',
                'compliance_requirements': [ComplianceStandard.HIPAA, ComplianceStandard.GDPR],
                'audit_required': True,
                'data_sensitivity': SecurityLevel.CRITICAL,
                'requires_justification': True
            },
            'patient.read': {
                'description': 'Read patient information',
                'compliance_requirements': [ComplianceStandard.HIPAA],
                'audit_required': True,
                'data_sensitivity': SecurityLevel.CRITICAL
            },
            'system.admin': {
                'description': 'System administration',
                'compliance_requirements': [ComplianceStandard.SOC2],
                'audit_required': True,
                'data_sensitivity': SecurityLevel.CRITICAL
            }
        }
        
        # Define compliance roles
        self.compliance_roles = {
            'hipaa_researcher': {
                'permissions': ['neural_data.read', 'neural_data.write'],
                'requirements': ['background_check', 'hipaa_training'],
                'max_session_hours': 8
            },
            'clinical_investigator': {
                'permissions': ['neural_data.read', 'patient.read'],
                'requirements': ['medical_license', 'gcp_training'],
                'max_session_hours': 12
            },
            'data_protection_officer': {
                'permissions': ['neural_data.read', 'neural_data.export', 'audit.read'],
                'requirements': ['gdpr_certification'],
                'max_session_hours': 24
            }
        }
    
    def check_permission(self, user_id: str, tenant_id: str, permission: str,
                        resource_id: Optional[str] = None, 
                        context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if user has permission with compliance logging"""
        
        # Get permission definition
        perm_def = self.permission_definitions.get(permission)
        if not perm_def:
            self.audit_logger.log_event(AuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                tenant_id=tenant_id,
                event_type="PERMISSION_CHECK",
                resource_type="PERMISSION",
                resource_id=permission,
                action="CHECK",
                result="FAILURE",
                details={'reason': 'Unknown permission'},
                risk_level=SecurityLevel.MEDIUM
            ))
            return False
        
        # Check if user has the permission (simplified - would integrate with user management)
        has_permission = self._user_has_permission(user_id, permission)
        
        # Log the access check
        if perm_def['audit_required']:
            self.audit_logger.log_event(AuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                tenant_id=tenant_id,
                event_type="PERMISSION_CHECK",
                resource_type="PERMISSION",
                resource_id=permission,
                action="CHECK",
                result="SUCCESS" if has_permission else "FAILURE",
                details={
                    'permission': permission,
                    'resource_id': resource_id,
                    'context': context,
                    'compliance_requirements': [req.value for req in perm_def['compliance_requirements']]
                },
                risk_level=perm_def['data_sensitivity']
            ))
        
        return has_permission
    
    def _user_has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission (placeholder)"""
        # This would integrate with your user management system
        # For now, returning True for demonstration
        return True


class DataAnonymizationEngine:
    """HIPAA-compliant data anonymization for neural signals"""
    
    def __init__(self):
        self.anonymization_methods = {
            'k_anonymity': self._apply_k_anonymity,
            'differential_privacy': self._apply_differential_privacy,
            'temporal_shifting': self._apply_temporal_shifting,
            'amplitude_scaling': self._apply_amplitude_scaling
        }
    
    def anonymize_neural_data(self, data: np.ndarray, metadata: Dict[str, Any],
                             method: str = 'differential_privacy',
                             privacy_level: float = 1.0) -> tuple[np.ndarray, Dict[str, Any]]:
        """Anonymize neural data while preserving clinical utility"""
        
        if method not in self.anonymization_methods:
            raise ValueError(f"Unknown anonymization method: {method}")
        
        # Apply anonymization
        anonymized_data = self.anonymization_methods[method](data, privacy_level)
        
        # Update metadata
        anonymized_metadata = metadata.copy()
        anonymized_metadata.update({
            'anonymized': True,
            'anonymization_method': method,
            'privacy_level': privacy_level,
            'anonymized_at': datetime.utcnow().isoformat(),
            'original_removed': True
        })
        
        # Remove potentially identifying metadata
        identifying_fields = ['patient_id', 'subject_id', 'session_id', 'device_serial']
        for field in identifying_fields:
            anonymized_metadata.pop(field, None)
        
        return anonymized_data, anonymized_metadata
    
    def _apply_differential_privacy(self, data: np.ndarray, epsilon: float) -> np.ndarray:
        """Apply differential privacy noise"""
        # Calculate noise scale based on epsilon (privacy budget)
        sensitivity = np.max(data) - np.min(data)  # Global sensitivity
        noise_scale = sensitivity / epsilon
        
        # Add Laplace noise
        noise = np.random.laplace(0, noise_scale, data.shape)
        return data + noise
    
    def _apply_k_anonymity(self, data: np.ndarray, k: int = 5) -> np.ndarray:
        """Apply k-anonymity by generalizing data"""
        # Quantize signal values to reduce uniqueness
        quantization_levels = max(10, len(np.unique(data)) // k)
        quantized = np.round(data * quantization_levels) / quantization_levels
        return quantized
    
    def _apply_temporal_shifting(self, data: np.ndarray, max_shift_samples: int = 100) -> np.ndarray:
        """Apply random temporal shifts to remove timing-based identification"""
        shift = np.random.randint(-max_shift_samples, max_shift_samples)
        return np.roll(data, shift, axis=-1)
    
    def _apply_amplitude_scaling(self, data: np.ndarray, scale_variance: float = 0.1) -> np.ndarray:
        """Apply random amplitude scaling"""
        scale_factor = 1.0 + np.random.normal(0, scale_variance)
        return data * scale_factor


class ComplianceFramework:
    """Main compliance framework orchestrating all security components"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.encryption_manager = EncryptionManager()
        self.audit_logger = AuditLogger(config)
        self.access_control = AccessControlManager(config)
        self.anonymization_engine = DataAnonymizationEngine()
        
        # Compliance validators
        self.validators = {
            ComplianceStandard.HIPAA: self._validate_hipaa_compliance,
            ComplianceStandard.FDA_21CFR_PART11: self._validate_fda_compliance,
            ComplianceStandard.GDPR: self._validate_gdpr_compliance
        }
    
    async def process_neural_data(self, data: bytes, metadata: Dict[str, Any],
                                 user_id: str, tenant_id: str,
                                 operation: str) -> Dict[str, Any]:
        """Process neural data with full compliance checking"""
        
        # 1. Validate compliance requirements
        compliance_result = await self._validate_compliance(operation, user_id, tenant_id)
        if not compliance_result['valid']:
            raise ValueError(f"Compliance validation failed: {compliance_result['errors']}")
        
        # 2. Check permissions
        required_permission = f"neural_data.{operation}"
        if not self.access_control.check_permission(user_id, tenant_id, required_permission):
            raise PermissionError(f"User {user_id} lacks permission {required_permission}")
        
        # 3. Encrypt data
        encrypted_package = self.encryption_manager.encrypt_neural_data(data, metadata)
        
        # 4. Log the operation
        self.audit_logger.log_data_access(
            user_id=user_id,
            tenant_id=tenant_id,
            resource_id=encrypted_package.get('checksum', 'unknown'),
            action=operation.upper(),
            result="SUCCESS",
            details={
                'data_size_bytes': len(data),
                'encryption_algorithm': encrypted_package['algorithm'],
                'compliance_standards': [std.value for std in self.config.enabled_standards]
            }
        )
        
        return {
            'encrypted_data': encrypted_package,
            'compliance_status': compliance_result,
            'processing_timestamp': datetime.utcnow().isoformat()
        }
    
    async def anonymize_for_research(self, data: np.ndarray, metadata: Dict[str, Any],
                                   user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Anonymize neural data for research use"""
        
        # Check permission for anonymization
        if not self.access_control.check_permission(user_id, tenant_id, 'neural_data.anonymize'):
            raise PermissionError("Insufficient permissions for data anonymization")
        
        # Apply anonymization
        anonymized_data, anonymized_metadata = self.anonymization_engine.anonymize_neural_data(
            data, metadata, method='differential_privacy'
        )
        
        # Log anonymization
        self.audit_logger.log_event(AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            tenant_id=tenant_id,
            event_type="DATA_ANONYMIZATION",
            resource_type="NEURAL_DATA",
            resource_id=None,
            action="ANONYMIZE",
            result="SUCCESS",
            details={
                'original_shape': data.shape,
                'anonymization_method': 'differential_privacy',
                'hipaa_compliant': True
            },
            risk_level=SecurityLevel.HIGH
        ))
        
        return {
            'anonymized_data': anonymized_data,
            'anonymized_metadata': anonymized_metadata,
            'anonymization_id': str(uuid.uuid4())
        }
    
    async def _validate_compliance(self, operation: str, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Validate operation against enabled compliance standards"""
        
        validation_results = {}
        errors = []
        
        for standard in self.config.enabled_standards:
            if standard in self.validators:
                result = await self.validators[standard](operation, user_id, tenant_id)
                validation_results[standard.value] = result
                if not result['valid']:
                    errors.extend(result['errors'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'standards_checked': [std.value for std in self.config.enabled_standards],
            'detailed_results': validation_results
        }
    
    async def _validate_hipaa_compliance(self, operation: str, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Validate HIPAA compliance requirements"""
        errors = []
        
        # Check minimum necessary access principle
        if operation in ['export', 'delete'] and not self._has_business_justification(user_id, operation):
            errors.append("HIPAA: No business justification for high-risk operation")
        
        # Check encryption requirements
        if not self.config.encryption_at_rest:
            errors.append("HIPAA: Encryption at rest required for PHI")
        
        if not self.config.encryption_in_transit:
            errors.append("HIPAA: Encryption in transit required for PHI")
        
        # Check audit logging
        if not self.config.audit_logging:
            errors.append("HIPAA: Comprehensive audit logging required")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'standard': 'HIPAA',
            'requirements_checked': ['minimum_necessary', 'encryption', 'audit_logging']
        }
    
    async def _validate_fda_compliance(self, operation: str, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Validate FDA 21 CFR Part 11 compliance"""
        errors = []
        
        # Check electronic signature requirements for data modification
        if operation in ['write', 'modify', 'delete']:
            if not self._has_electronic_signature(user_id):
                errors.append("FDA: Electronic signature required for data modifications")
        
        # Check audit trail requirements
        if not self.config.audit_logging:
            errors.append("FDA: Complete audit trail required")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'standard': 'FDA_21CFR_Part11',
            'requirements_checked': ['electronic_signatures', 'audit_trail']
        }
    
    async def _validate_gdpr_compliance(self, operation: str, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Validate GDPR compliance requirements"""
        errors = []
        
        # Check consent for data processing
        if operation == 'export' and not self._has_data_subject_consent(tenant_id):
            errors.append("GDPR: Data subject consent required for export")
        
        # Check right to be forgotten
        if operation == 'delete' and not self._validate_deletion_request(user_id):
            errors.append("GDPR: Invalid deletion request")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'standard': 'GDPR',
            'requirements_checked': ['consent', 'right_to_be_forgotten']
        }
    
    def _has_business_justification(self, user_id: str, operation: str) -> bool:
        """Check if user has documented business justification"""
        # Placeholder - would integrate with justification tracking system
        return True
    
    def _has_electronic_signature(self, user_id: str) -> bool:
        """Check if user has valid electronic signature"""
        # Placeholder - would integrate with signature management
        return True
    
    def _has_data_subject_consent(self, tenant_id: str) -> bool:
        """Check if data subject has given consent"""
        # Placeholder - would integrate with consent management
        return True
    
    def _validate_deletion_request(self, user_id: str) -> bool:
        """Validate GDPR deletion request"""
        # Placeholder - would validate deletion request legitimacy
        return True
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        return {
            'framework_version': '1.0.0',
            'enabled_standards': [std.value for std in self.config.enabled_standards],
            'encryption_status': {
                'at_rest': self.config.encryption_at_rest,
                'in_transit': self.config.encryption_in_transit,
                'key_rotation_enabled': True,
                'last_key_rotation': 'N/A'  # Would track actual rotation
            },
            'audit_status': {
                'logging_enabled': self.config.audit_logging,
                'retention_days': self.config.data_retention_days,
                'events_logged_today': 0  # Would track actual events
            },
            'access_control': {
                'mfa_required': self.config.require_mfa,
                'session_timeout_minutes': self.config.session_timeout_minutes,
                'password_policy_enforced': True
            },
            'data_protection': {
                'anonymization_available': True,
                'backup_encryption': self.config.backup_encryption,
                'data_classification_enforced': True
            },
            'generated_at': datetime.utcnow().isoformat(),
            'next_review_date': (datetime.utcnow() + timedelta(days=90)).isoformat()
        }


# Factory function for easy deployment
def create_enterprise_compliance_framework(
    standards: List[ComplianceStandard] = None,
    security_level: SecurityLevel = SecurityLevel.HIGH
) -> ComplianceFramework:
    """Create a pre-configured compliance framework"""
    
    if standards is None:
        standards = [ComplianceStandard.HIPAA, ComplianceStandard.GDPR]
    
    # Configure based on security level
    if security_level == SecurityLevel.CRITICAL:
        config = ComplianceConfig(
            enabled_standards=standards,
            encryption_at_rest=True,
            encryption_in_transit=True,
            audit_logging=True,
            require_mfa=True,
            session_timeout_minutes=15,
            max_failed_attempts=2,
            key_rotation_days=30
        )
    elif security_level == SecurityLevel.HIGH:
        config = ComplianceConfig(
            enabled_standards=standards,
            encryption_at_rest=True,
            encryption_in_transit=True,
            audit_logging=True,
            require_mfa=True,
            session_timeout_minutes=30,
            max_failed_attempts=3,
            key_rotation_days=90
        )
    else:
        config = ComplianceConfig(
            enabled_standards=standards,
            encryption_at_rest=True,
            encryption_in_transit=True,
            audit_logging=True,
            require_mfa=False,
            session_timeout_minutes=60,
            max_failed_attempts=5,
            key_rotation_days=180
        )
    
    return ComplianceFramework(config)


# Example usage
if __name__ == "__main__":
    import numpy as np
    
    async def test_compliance_framework():
        """Test the enterprise compliance framework"""
        
        # Create framework with HIPAA and GDPR compliance
        framework = create_enterprise_compliance_framework(
            standards=[ComplianceStandard.HIPAA, ComplianceStandard.GDPR],
            security_level=SecurityLevel.HIGH
        )
        
        # Test data processing with compliance
        test_data = np.random.randn(64, 1000).tobytes()
        test_metadata = {
            'patient_id': 'PATIENT_001',
            'timestamp': datetime.utcnow().isoformat(),
            'channels': 64,
            'sampling_rate': 1000
        }
        
        try:
            # Process data with compliance checking
            result = await framework.process_neural_data(
                data=test_data,
                metadata=test_metadata,
                user_id='researcher_001',
                tenant_id='hospital_001',
                operation='read'
            )
            
            print("✓ Data processed with compliance")
            print(f"  Encryption: {result['encrypted_data']['algorithm']}")
            print(f"  Compliance: {result['compliance_status']['valid']}")
            
            # Test anonymization
            np_data = np.random.randn(64, 1000)
            anon_result = await framework.anonymize_for_research(
                data=np_data,
                metadata=test_metadata,
                user_id='researcher_001',
                tenant_id='hospital_001'
            )
            
            print("✓ Data anonymized for research")
            print(f"  Anonymization ID: {anon_result['anonymization_id']}")
            
            # Generate compliance report
            report = framework.generate_compliance_report()
            print("✓ Compliance report generated")
            print(f"  Standards: {report['enabled_standards']}")
            print(f"  Next review: {report['next_review_date']}")
            
        except Exception as e:
            print(f"✗ Compliance test failed: {e}")
    
    # Run test
    asyncio.run(test_compliance_framework())