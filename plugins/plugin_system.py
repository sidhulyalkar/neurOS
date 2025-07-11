# neuros/core/plugins/plugin_system.py
"""
Advanced Plugin Architecture for neurOS
Extensible component system with hot-loading and dependency management
"""

import importlib
import inspect
import json
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Type, Optional, Callable
from dataclasses import dataclass, field
import logging
from enum import Enum
import asyncio
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

class PluginType(Enum):
    """Types of plugins supported by neurOS"""
    SIGNAL_PROCESSOR = "signal_processor"
    FEATURE_EXTRACTOR = "feature_extractor"
    CLASSIFIER = "classifier"
    HARDWARE_INTERFACE = "hardware_interface"
    DATA_VISUALIZER = "data_visualizer"
    SECURITY_MODULE = "security_module"
    API_ENDPOINT = "api_endpoint"
    CUSTOM = "custom"

class PluginStatus(Enum):
    """Plugin status states"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class PluginManifest:
    """Plugin manifest containing metadata"""
    name: str
    version: str
    plugin_type: PluginType
    author: str
    description: str
    entry_point: str
    dependencies: List[str] = field(default_factory=list)
    api_version: str = "1.0.0"
    permissions: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    min_neuros_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PluginInstance:
    """Runtime plugin instance"""
    manifest: PluginManifest
    plugin_class: Type
    instance: Any = None
    status: PluginStatus = PluginStatus.UNLOADED
    config: Dict[str, Any] = field(default_factory=dict)
    load_time: Optional[datetime] = None
    error_message: Optional[str] = None

class PluginInterface(ABC):
    """Base interface for all neurOS plugins"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(f"plugin.{self.name}")
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin"""
        pass
        
    @abstractmethod
    async def cleanup(self) -> bool:
        """Cleanup plugin resources"""
        pass
        
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information"""
        return {
            "name": self.name,
            "config": self.config,
            "status": "active"
        }

class SignalProcessorPlugin(PluginInterface):
    """Base class for signal processing plugins"""
    
    @abstractmethod
    async def process(self, data: Any, **kwargs) -> Any:
        """Process signal data"""
        pass

class FeatureExtractorPlugin(PluginInterface):
    """Base class for feature extraction plugins"""
    
    @abstractmethod
    async def extract_features(self, data: Any, **kwargs) -> Any:
        """Extract features from data"""
        pass

class ClassifierPlugin(PluginInterface):
    """Base class for classifier plugins"""
    
    @abstractmethod
    async def train(self, X: Any, y: Any, **kwargs) -> bool:
        """Train the classifier"""
        pass
        
    @abstractmethod
    async def predict(self, X: Any, **kwargs) -> Any:
        """Make predictions"""
        pass

class HardwareInterfacePlugin(PluginInterface):
    """Base class for hardware interface plugins"""
    
    @abstractmethod
    async def connect(self, **kwargs) -> bool:
        """Connect to hardware"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from hardware"""
        pass
        
    @abstractmethod
    async def read_data(self, **kwargs) -> Any:
        """Read data from hardware"""
        pass

class PluginRegistry:
    """Registry for managing plugin discovery and metadata"""
    
    def __init__(self):
        self._plugins: Dict[str, PluginInstance] = {}
        self._plugin_paths: List[Path] = []
        self._watchers: List[threading.Thread] = []
        
    def add_plugin_path(self, path: Path):
        """Add a path to search for plugins"""
        if path.exists() and path.is_dir():
            self._plugin_paths.append(path)
            logger.info(f"Added plugin path: {path}")
        
    def discover_plugins(self) -> List[PluginManifest]:
        """Discover plugins in registered paths"""
        discovered = []
        
        for plugin_path in self._plugin_paths:
            for manifest_file in plugin_path.rglob("plugin.yaml"):
                try:
                    manifest = self._load_manifest(manifest_file)
                    discovered.append(manifest)
                    logger.info(f"Discovered plugin: {manifest.name}")
                except Exception as e:
                    logger.error(f"Failed to load manifest {manifest_file}: {e}")
        
        return discovered
    
    def _load_manifest(self, manifest_file: Path) -> PluginManifest:
        """Load plugin manifest from file"""
        with open(manifest_file, 'r') as f:
            data = yaml.safe_load(f)
        
        return PluginManifest(
            name=data['name'],
            version=data['version'],
            plugin_type=PluginType(data['type']),
            author=data['author'],
            description=data['description'],
            entry_point=data['entry_point'],
            dependencies=data.get('dependencies', []),
            api_version=data.get('api_version', '1.0.0'),
            permissions=data.get('permissions', []),
            config_schema=data.get('config_schema', {}),
            min_neuros_version=data.get('min_neuros_version', '1.0.0'),
            metadata=data.get('metadata', {})
        )
    
    def register_plugin(self, plugin_instance: PluginInstance):
        """Register a plugin instance"""
        self._plugins[plugin_instance.manifest.name] = plugin_instance
        
    def get_plugin(self, name: str) -> Optional[PluginInstance]:
        """Get plugin by name"""
        return self._plugins.get(name)
    
    def list_plugins(self, plugin_type: Optional[PluginType] = None) -> List[PluginInstance]:
        """List registered plugins"""
        plugins = list(self._plugins.values())
        if plugin_type:
            plugins = [p for p in plugins if p.manifest.plugin_type == plugin_type]
        return plugins

class PluginManager:
    """Main plugin management system"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".neuros" / "plugins"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry = PluginRegistry()
        self.dependency_resolver = DependencyResolver()
        self.security_manager = PluginSecurityManager()
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # Add default plugin paths
        self.registry.add_plugin_path(Path(__file__).parent / "builtin")
        self.registry.add_plugin_path(self.config_dir / "installed")
        
    async def initialize(self):
        """Initialize the plugin system"""
        logger.info("Initializing plugin system...")
        
        # Discover and load plugins
        discovered = self.registry.discover_plugins()
        for manifest in discovered:
            try:
                await self.load_plugin(manifest)
            except Exception as e:
                logger.error(f"Failed to load plugin {manifest.name}: {e}")
        
        logger.info(f"Plugin system initialized with {len(self.registry.list_plugins())} plugins")
    
    async def load_plugin(self, manifest: PluginManifest, config: Dict[str, Any] = None) -> bool:
        """Load a plugin from manifest"""
        try:
            # Validate security permissions
            if not self.security_manager.validate_permissions(manifest.permissions):
                raise PermissionError(f"Plugin {manifest.name} has insufficient permissions")
            
            # Resolve dependencies
            resolved_deps = await self.dependency_resolver.resolve(manifest.dependencies)
            if not resolved_deps:
                raise ImportError(f"Failed to resolve dependencies for {manifest.name}")
            
            # Load plugin class
            plugin_class = self._load_plugin_class(manifest)
            
            # Create plugin instance
            plugin_instance = PluginInstance(
                manifest=manifest,
                plugin_class=plugin_class,
                config=config or {},
                status=PluginStatus.LOADED,
                load_time=datetime.now()
            )
            
            # Initialize plugin
            plugin_instance.instance = plugin_class(plugin_instance.config)
            if await plugin_instance.instance.initialize():
                plugin_instance.status = PluginStatus.ACTIVE
                self.registry.register_plugin(plugin_instance)
                
                # Emit plugin loaded event
                await self._emit_event("plugin_loaded", plugin_instance)
                
                logger.info(f"Successfully loaded plugin: {manifest.name}")
                return True
            else:
                plugin_instance.status = PluginStatus.ERROR
                plugin_instance.error_message = "Initialization failed"
                return False
                
        except Exception as e:
            logger.error(f"Failed to load plugin {manifest.name}: {e}")
            return False
    
    def _load_plugin_class(self, manifest: PluginManifest) -> Type[PluginInterface]:
        """Dynamically load plugin class"""
        module_path, class_name = manifest.entry_point.rsplit('.', 1)
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        
        # Validate plugin interface
        if not issubclass(plugin_class, PluginInterface):
            raise TypeError(f"Plugin {manifest.name} must inherit from PluginInterface")
        
        return plugin_class
    
    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin"""
        plugin_instance = self.registry.get_plugin(name)
        if not plugin_instance:
            return False
        
        try:
            if plugin_instance.instance:
                await plugin_instance.instance.cleanup()
            
            plugin_instance.status = PluginStatus.UNLOADED
            await self._emit_event("plugin_unloaded", plugin_instance)
            
            logger.info(f"Successfully unloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return False
    
    async def reload_plugin(self, name: str) -> bool:
        """Reload a plugin"""
        plugin_instance = self.registry.get_plugin(name)
        if not plugin_instance:
            return False
        
        # Store config
        config = plugin_instance.config
        
        # Unload and reload
        if await self.unload_plugin(name):
            return await self.load_plugin(plugin_instance.manifest, config)
        
        return False
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInstance]:
        """Get all plugins of a specific type"""
        return self.registry.list_plugins(plugin_type)
    
    async def execute_plugin_method(self, name: str, method: str, *args, **kwargs) -> Any:
        """Execute a method on a plugin"""
        plugin_instance = self.registry.get_plugin(name)
        if not plugin_instance or plugin_instance.status != PluginStatus.ACTIVE:
            raise RuntimeError(f"Plugin {name} is not active")
        
        if not hasattr(plugin_instance.instance, method):
            raise AttributeError(f"Plugin {name} has no method {method}")
        
        method_func = getattr(plugin_instance.instance, method)
        if asyncio.iscoroutinefunction(method_func):
            return await method_func(*args, **kwargs)
        else:
            return method_func(*args, **kwargs)
    
    def add_event_handler(self, event: str, handler: Callable):
        """Add event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    async def _emit_event(self, event: str, data: Any):
        """Emit plugin event"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")

class DependencyResolver:
    """Resolve plugin dependencies"""
    
    async def resolve(self, dependencies: List[str]) -> bool:
        """Resolve list of dependencies"""
        for dep in dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                logger.error(f"Failed to resolve dependency: {dep}")
                return False
        return True

class PluginSecurityManager:
    """Security manager for plugins"""
    
    def __init__(self):
        self.allowed_permissions = {
            "hardware_access",
            "file_system",
            "network_access",
            "system_info",
            "data_processing"
        }
    
    def validate_permissions(self, permissions: List[str]) -> bool:
        """Validate plugin permissions"""
        for permission in permissions:
            if permission not in self.allowed_permissions:
                logger.warning(f"Unknown permission requested: {permission}")
                return False
        return True

# Example Plugin Implementations
class ExampleSignalFilterPlugin(SignalProcessorPlugin):
    """Example signal filtering plugin"""
    
    async def initialize(self) -> bool:
        self.filter_type = self.config.get("filter_type", "butterworth")
        self.cutoff_freq = self.config.get("cutoff_freq", 40)
        return True
    
    async def cleanup(self) -> bool:
        return True
    
    async def process(self, data: Any, **kwargs) -> Any:
        """Apply filtering to signal data"""
        import numpy as np
        from scipy import signal
        
        # Simple bandpass filter example
        sos = signal.butter(4, [1, self.cutoff_freq], btype='band', fs=250, output='sos')
        filtered_data = signal.sosfilt(sos, data, axis=-1)
        
        return filtered_data

class ExampleFeatureExtractorPlugin(FeatureExtractorPlugin):
    """Example feature extraction plugin"""
    
    async def initialize(self) -> bool:
        self.feature_types = self.config.get("features", ["bandpower", "entropy"])
        return True
    
    async def cleanup(self) -> bool:
        return True
    
    async def extract_features(self, data: Any, **kwargs) -> Any:
        """Extract features from data"""
        import numpy as np
        
        features = []
        
        if "bandpower" in self.feature_types:
            # Simple bandpower calculation
            power = np.mean(np.abs(data) ** 2, axis=-1)
            features.extend(power.flatten())
        
        if "entropy" in self.feature_types:
            # Simple entropy calculation
            entropy = -np.sum(data * np.log(data + 1e-10), axis=-1)
            features.extend(entropy.flatten())
        
        return np.array(features)

class PluginAPI:
    """API for plugin management"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
    
    async def list_plugins(self) -> Dict[str, Any]:
        """List all plugins with status"""
        plugins = self.plugin_manager.registry.list_plugins()
        return {
            "plugins": [
                {
                    "name": p.manifest.name,
                    "version": p.manifest.version,
                    "type": p.manifest.plugin_type.value,
                    "status": p.status.value,
                    "description": p.manifest.description,
                    "load_time": p.load_time.isoformat() if p.load_time else None,
                    "error": p.error_message
                }
                for p in plugins
            ]
        }
    
    async def install_plugin(self, plugin_package: str) -> Dict[str, Any]:
        """Install plugin from package"""
        # This would integrate with package managers like pip
        # For now, return a mock response
        return {
            "success": True,
            "message": f"Plugin {plugin_package} installed successfully",
            "plugin_name": plugin_package
        }
    
    async def configure_plugin(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure plugin settings"""
        plugin_instance = self.plugin_manager.registry.get_plugin(name)
        if not plugin_instance:
            return {"success": False, "error": "Plugin not found"}
        
        plugin_instance.config.update(config)
        
        # Reload plugin with new config
        success = await self.plugin_manager.reload_plugin(name)
        
        return {
            "success": success,
            "message": f"Plugin {name} configured successfully" if success else "Configuration failed"
        }

# Plugin CLI Commands
class PluginCLI:
    """Command-line interface for plugin management"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
    
    async def list_command(self):
        """List all plugins"""
        plugins = self.plugin_manager.registry.list_plugins()
        
        print("\n🔌 neurOS Plugins")
        print("=" * 50)
        
        for plugin in plugins:
            status_icon = {
                PluginStatus.ACTIVE: "✅",
                PluginStatus.LOADED: "⏸️",
                PluginStatus.ERROR: "❌",
                PluginStatus.DISABLED: "🚫",
                PluginStatus.UNLOADED: "⭕"
            }.get(plugin.status, "❓")
            
            print(f"{status_icon} {plugin.manifest.name} v{plugin.manifest.version}")
            print(f"   Type: {plugin.manifest.plugin_type.value}")
            print(f"   Status: {plugin.status.value}")
            print(f"   Description: {plugin.manifest.description}")
            if plugin.error_message:
                print(f"   Error: {plugin.error_message}")
            print()
    
    async def install_command(self, plugin_path: str):
        """Install plugin from path"""
        try:
            manifest_file = Path(plugin_path) / "plugin.yaml"
            if not manifest_file.exists():
                print(f"❌ No plugin.yaml found in {plugin_path}")
                return
            
            manifest = self.plugin_manager.registry._load_manifest(manifest_file)
            success = await self.plugin_manager.load_plugin(manifest)
            
            if success:
                print(f"✅ Successfully installed plugin: {manifest.name}")
            else:
                print(f"❌ Failed to install plugin: {manifest.name}")
                
        except Exception as e:
            print(f"❌ Installation failed: {e}")
    
    async def enable_command(self, plugin_name: str):
        """Enable a plugin"""
        plugin_instance = self.plugin_manager.registry.get_plugin(plugin_name)
        if not plugin_instance:
            print(f"❌ Plugin not found: {plugin_name}")
            return
        
        if plugin_instance.status == PluginStatus.ACTIVE:
            print(f"ℹ️ Plugin {plugin_name} is already active")
            return
        
        success = await self.plugin_manager.load_plugin(plugin_instance.manifest, plugin_instance.config)
        
        if success:
            print(f"✅ Successfully enabled plugin: {plugin_name}")
        else:
            print(f"❌ Failed to enable plugin: {plugin_name}")
    
    async def disable_command(self, plugin_name: str):
        """Disable a plugin"""
        success = await self.plugin_manager.unload_plugin(plugin_name)
        
        if success:
            print(f"✅ Successfully disabled plugin: {plugin_name}")
        else:
            print(f"❌ Failed to disable plugin: {plugin_name}")