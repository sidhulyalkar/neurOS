# core/security/access_control.py
class PermissionSystem:
    """Fine-grained permission control for neural data"""
    
    def __init__(self):
        self.permissions = {
            "raw_signal_read": "Read raw neural signals",
            "processed_signal_read": "Read processed signals",
            "model_execute": "Execute ML models",
            "device_control": "Control BCI devices",
            "llm_access": "Access LLM features",
            "data_export": "Export neural data",
            "realtime_stream": "Access real-time streams"
        }
        
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        resource: Any
    ) -> bool:
        """Check if user has permission for resource"""
        # Get user roles
        roles = await self._get_user_roles(user_id)
        
        # Check role-based permissions
        for role in roles:
            if await self._role_has_permission(role, permission):
                # Check resource-specific rules
                if await self._check_resource_rules(user_id, resource):
                    return True
                    
        return False