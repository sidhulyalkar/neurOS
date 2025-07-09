# core/runtime/resource_monitor.py
class ResourceMonitor:
    """Monitor and enforce resource limits"""
    
    def __init__(self):
        self._active_monitors = {}
        
    def monitor(self, context: ExecutionContext):
        """Context manager for resource monitoring"""
        return ResourceContext(self, context)
        
class ResourceContext:
    """Resource monitoring context"""
    
    def __init__(self, monitor: ResourceMonitor, context: ExecutionContext):
        self.monitor = monitor
        self.context = context
        self.start_time = None
        self.start_memory = None
        
    async def __aenter__(self):
        self.start_time = asyncio.get_event_loop().time()
        self.start_memory = self._get_memory_usage()
        
        # Start monitoring tasks
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._monitor_task.cancel()
        
    async def _monitor_loop(self):
        """Continuous resource monitoring"""
        while True:
            # Check CPU time
            elapsed = asyncio.get_event_loop().time() - self.start_time
            if elapsed > self.context.resource_limits.get("max_cpu_time", 60):
                raise ResourceExceeded("CPU time limit exceeded")
                
            # Check memory
            current_memory = self._get_memory_usage()
            memory_delta = current_memory - self.start_memory
            if memory_delta > self.context.resource_limits.get("max_memory_mb", 512) * 1024 * 1024:
                raise ResourceExceeded("Memory limit exceeded")
                
            await asyncio.sleep(0.1)