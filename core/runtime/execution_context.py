# core/runtime/execution_context.py
@dataclass
class ExecutionContext:
    """Context for running BCI applications"""
    user_id: str
    session_id: str
    devices: List[str]  # device IDs
    permissions: Dict[str, bool]
    resource_limits: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

class RuntimeEnvironment:
    """Sandboxed runtime for BCI applications"""
    
    def __init__(self):
        self._contexts: Dict[str, ExecutionContext] = {}
        self._resource_monitor = ResourceMonitor()
        self._security_manager = SecurityManager()
        
    async def create_context(self, user_id: str, app_manifest: Dict[str, Any]) -> ExecutionContext:
        """Create new execution context for app"""
        # Validate permissions
        permissions = self._security_manager.validate_permissions(
            app_manifest.get("permissions", [])
        )
        
        # Set resource limits
        resource_limits = self._calculate_resource_limits(app_manifest)
        
        context = ExecutionContext(
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            devices=[],
            permissions=permissions,
            resource_limits=resource_limits
        )
        
        self._contexts[context.session_id] = context
        return context
        
    async def execute_app(self, context: ExecutionContext, app_code: str) -> Any:
        """Execute app in sandboxed environment"""
        # Create restricted globals
        sandbox_globals = self._create_sandbox_globals(context)
        
        # Monitor resources
        with self._resource_monitor.monitor(context):
            # Execute with timeout
            return await asyncio.wait_for(
                self._execute_sandboxed(app_code, sandbox_globals),
                timeout=context.resource_limits.get("max_execution_time", 30)
            )
            
    def _create_sandbox_globals(self, context: ExecutionContext) -> Dict[str, Any]:
        """Create restricted global namespace for app execution"""
        return {
            "__builtins__": self._create_safe_builtins(),
            "neuros": self._create_api_proxy(context),
            "np": self._create_safe_numpy(),
            "context": context
        }