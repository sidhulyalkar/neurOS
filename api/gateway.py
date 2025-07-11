# neuros/api/gateway.py
"""
REST API Gateway for neurOS
Comprehensive API with authentication, rate limiting, and monitoring
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import asyncio
import time
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
import redis
import jwt
from passlib.context import CryptContext
import aiofiles
import numpy as np
from contextlib import asynccontextmanager

# neurOS imports
from ..core.pipeline.enhanced_pipeline import EnhancedPipeline, PipelineConfig
from ..enterprise.security import SecurityManager, AuditLogger
from ..core.plugins.plugin_system import PluginManager
from ..agents.framework import AgentManager

logger = logging.getLogger(__name__)

# Pydantic Models
class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    data: Any = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None

class PipelineRequest(BaseModel):
    """Pipeline creation request"""
    name: str
    mode: str = "realtime"
    latency_target_ms: int = 50
    config: Dict[str, Any] = {}

class ProcessingRequest(BaseModel):
    """Data processing request"""
    data: List[List[float]]
    pipeline_id: str
    parameters: Dict[str, Any] = {}

class UserCredentials(BaseModel):
    """User authentication credentials"""
    username: str
    password: str

class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 100
    burst_size: int = 10
    window_size: int = 60

class RateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self, redis_client, config: RateLimitConfig):
        self.redis = redis_client
        self.config = config
    
    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        try:
            pipe = self.redis.pipeline()
            now = time.time()
            window_start = now - self.config.window_size
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry
            pipe.expire(key, self.config.window_size)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            return current_requests < self.config.requests_per_minute
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True  # Allow on error

class AuthenticationManager:
    """JWT-based authentication manager"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.users_db = {}  # In production, use proper database
    
    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(hours=1))
        to_encode.update({"exp": expire})
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return self.pwd_context.verify(plain_password, hashed_password)

class APIGateway:
    """Main API Gateway class"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.app = FastAPI(
            title="neurOS API Gateway",
            description="Enterprise BCI Operating System API",
            version="1.0.0",
            lifespan=self._lifespan
        )
        
        # Initialize components
        self.redis_client = None
        self.rate_limiter = None
        self.auth_manager = AuthenticationManager(
            self.config.get("secret_key", "neuros-secret-key-change-in-production")
        )
        self.security_manager = SecurityManager()
        self.audit_logger = AuditLogger()
        self.plugin_manager = PluginManager()
        self.agent_manager = AgentManager()
        
        # Active pipelines and sessions
        self.active_pipelines: Dict[str, EnhancedPipeline] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        self._setup_middleware()
        self._setup_routes()
    
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Application lifespan manager"""
        # Startup
        await self._startup()
        yield
        # Shutdown
        await self._shutdown()
    
    async def _startup(self):
        """Initialize services on startup"""
        logger.info("Starting neurOS API Gateway...")
        
        # Initialize Redis for rate limiting
        try:
            import aioredis
            self.redis_client = aioredis.from_url(
                self.config.get("redis_url", "redis://localhost:6379")
            )
            self.rate_limiter = RateLimiter(
                self.redis_client,
                RateLimitConfig(**self.config.get("rate_limit", {}))
            )
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
        
        # Initialize plugin system
        await self.plugin_manager.initialize()
        
        # Initialize agent system
        await self.agent_manager.initialize()
        
        logger.info("neurOS API Gateway started successfully")
    
    async def _shutdown(self):
        """Cleanup on shutdown"""
        logger.info("Shutting down neurOS API Gateway...")
        
        # Close active pipelines
        for pipeline in self.active_pipelines.values():
            try:
                await pipeline.cleanup()
            except Exception as e:
                logger.error(f"Pipeline cleanup error: {e}")
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("neurOS API Gateway shutdown complete")
    
    def _setup_middleware(self):
        """Setup middleware"""
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("allowed_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Compression
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Request logging and rate limiting
        @self.app.middleware("http")
        async def request_middleware(request: Request, call_next):
            start_time = time.time()
            request_id = f"req_{int(start_time * 1000)}"
            
            # Rate limiting
            if self.rate_limiter:
                client_ip = request.client.host
                if not await self.rate_limiter.is_allowed(f"rate_limit:{client_ip}"):
                    return JSONResponse(
                        status_code=429,
                        content={"error": "Rate limit exceeded"}
                    )
            
            # Process request
            response = await call_next(request)
            
            # Log request
            process_time = time.time() - start_time
            logger.info(
                f"{request.method} {request.url} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s - "
                f"ID: {request_id}"
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
    
    def _setup_routes(self):
        """Setup API routes"""
        
        # Authentication dependency
        security = HTTPBearer()
        
        async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
            payload = self.auth_manager.verify_token(credentials.credentials)
            return payload.get("sub")
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return APIResponse(
                success=True,
                data={
                    "status": "healthy",
                    "timestamp": datetime.now(),
                    "version": "1.0.0",
                    "components": {
                        "redis": self.redis_client is not None,
                        "plugins": len(self.plugin_manager.registry.list_plugins()),
                        "pipelines": len(self.active_pipelines),
                        "sessions": len(self.active_sessions)
                    }
                }
            )
        
        # Authentication endpoints
        @self.app.post("/auth/login", response_model=TokenResponse)
        async def login(credentials: UserCredentials):
            # In production, validate against proper user database
            if credentials.username == "admin" and credentials.password == "admin":
                access_token = self.auth_manager.create_access_token(
                    data={"sub": credentials.username}
                )
                refresh_token = self.auth_manager.create_access_token(
                    data={"sub": credentials.username, "type": "refresh"},
                    expires_delta=timedelta(days=7)
                )
                
                self.audit_logger.log_login_attempt(credentials.username, True)
                
                return TokenResponse(
                    access_token=access_token,
                    expires_in=3600,
                    refresh_token=refresh_token
                )
            else:
                self.audit_logger.log_login_attempt(credentials.username, False)
                raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Pipeline management
        @self.app.post("/pipelines", response_model=APIResponse)
        async def create_pipeline(
            request: PipelineRequest,
            current_user: str = Depends(get_current_user)
        ):
            try:
                config = PipelineConfig(
                    name=request.name,
                    mode=request.mode,
                    latency_target_ms=request.latency_target_ms,
                    **request.config
                )
                
                pipeline = EnhancedPipeline(config)
                await pipeline.initialize()
                
                pipeline_id = f"pipeline_{len(self.active_pipelines) + 1}"
                self.active_pipelines[pipeline_id] = pipeline
                
                self.audit_logger.log_data_access(
                    current_user, f"pipeline:{pipeline_id}", "create"
                )
                
                return APIResponse(
                    success=True,
                    data={
                        "pipeline_id": pipeline_id,
                        "name": request.name,
                        "status": "active"
                    },
                    message="Pipeline created successfully"
                )
                
            except Exception as e:
                logger.error(f"Pipeline creation failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/pipelines", response_model=APIResponse)
        async def list_pipelines(current_user: str = Depends(get_current_user)):
            pipelines_info = []
            for pipeline_id, pipeline in self.active_pipelines.items():
                pipelines_info.append({
                    "id": pipeline_id,
                    "name": pipeline.config.name,
                    "mode": pipeline.config.mode,
                    "status": "active",
                    "created_at": datetime.now().isoformat()
                })
            
            return APIResponse(
                success=True,
                data={"pipelines": pipelines_info}
            )
        
        @self.app.delete("/pipelines/{pipeline_id}", response_model=APIResponse)
        async def delete_pipeline(
            pipeline_id: str,
            current_user: str = Depends(get_current_user)
        ):
            if pipeline_id not in self.active_pipelines:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            try:
                pipeline = self.active_pipelines[pipeline_id]
                await pipeline.cleanup()
                del self.active_pipelines[pipeline_id]
                
                self.audit_logger.log_data_access(
                    current_user, f"pipeline:{pipeline_id}", "delete"
                )
                
                return APIResponse(
                    success=True,
                    message="Pipeline deleted successfully"
                )
                
            except Exception as e:
                logger.error(f"Pipeline deletion failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Data processing
        @self.app.post("/process", response_model=APIResponse)
        async def process_data(
            request: ProcessingRequest,
            background_tasks: BackgroundTasks,
            current_user: str = Depends(get_current_user)
        ):
            if request.pipeline_id not in self.active_pipelines:
                raise HTTPException(status_code=404, detail="Pipeline not found")
            
            try:
                pipeline = self.active_pipelines[request.pipeline_id]
                
                # Convert data to numpy array
                data = np.array(request.data)
                
                # Process data through pipeline
                result = await pipeline.process_data(data, **request.parameters)
                
                # Log processing
                background_tasks.add_task(
                    self.audit_logger.log_data_access,
                    current_user,
                    f"pipeline:{request.pipeline_id}",
                    "process"
                )
                
                return APIResponse(
                    success=True,
                    data={
                        "result": result.tolist() if hasattr(result, 'tolist') else result,
                        "pipeline_id": request.pipeline_id,
                        "data_shape": data.shape
                    },
                    message="Data processed successfully"
                )
                
            except Exception as e:
                logger.error(f"Data processing failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Plugin management
        @self.app.get("/plugins", response_model=APIResponse)
        async def list_plugins(current_user: str = Depends(get_current_user)):
            plugins = self.plugin_manager.registry.list_plugins()
            plugins_info = []
            
            for plugin in plugins:
                plugins_info.append({
                    "name": plugin.manifest.name,
                    "version": plugin.manifest.version,
                    "type": plugin.manifest.plugin_type.value,
                    "status": plugin.status.value,
                    "description": plugin.manifest.description
                })
            
            return APIResponse(
                success=True,
                data={"plugins": plugins_info}
            )
        
        @self.app.post("/plugins/{plugin_name}/execute", response_model=APIResponse)
        async def execute_plugin(
            plugin_name: str,
            method: str,
            parameters: Dict[str, Any] = {},
            current_user: str = Depends(get_current_user)
        ):
            try:
                result = await self.plugin_manager.execute_plugin_method(
                    plugin_name, method, **parameters
                )
                
                return APIResponse(
                    success=True,
                    data={"result": result},
                    message=f"Plugin {plugin_name} executed successfully"
                )
                
            except Exception as e:
                logger.error(f"Plugin execution failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # System metrics
        @self.app.get("/metrics", response_model=APIResponse)
        async def get_metrics(current_user: str = Depends(get_current_user)):
            metrics = {
                "system": {
                    "active_pipelines": len(self.active_pipelines),
                    "active_sessions": len(self.active_sessions),
                    "loaded_plugins": len(self.plugin_manager.registry.list_plugins()),
                    "uptime": time.time() - self._start_time if hasattr(self, '_start_time') else 0
                },
                "performance": {
                    "avg_response_time": 45.2,  # Mock data
                    "requests_per_minute": 128,
                    "error_rate": 0.02
                },
                "resources": {
                    "cpu_usage": 65.4,
                    "memory_usage": 72.1,
                    "disk_usage": 45.8
                }
            }
            
            return APIResponse(
                success=True,
                data=metrics
            )
        
        # Real-time streaming
        @self.app.websocket("/ws/stream/{pipeline_id}")
        async def websocket_stream(websocket, pipeline_id: str):
            await websocket.accept()
            
            if pipeline_id not in self.active_pipelines:
                await websocket.send_json({
                    "error": "Pipeline not found",
                    "pipeline_id": pipeline_id
                })
                await websocket.close()
                return
            
            try:
                pipeline = self.active_pipelines[pipeline_id]
                
                while True:
                    # Simulate real-time data streaming
                    await asyncio.sleep(0.1)  # 10Hz streaming
                    
                    # Generate mock data
                    mock_data = {
                        "timestamp": datetime.now().isoformat(),
                        "pipeline_id": pipeline_id,
                        "data": np.random.randn(8, 100).tolist(),  # 8 channels, 100 samples
                        "metrics": {
                            "latency": np.random.normal(45, 5),
                            "quality": np.random.uniform(0.8, 1.0)
                        }
                    }
                    
                    await websocket.send_json(mock_data)
                    
            except Exception as e:
                logger.error(f"WebSocket streaming error: {e}")
                await websocket.close()
        
        # File upload/download
        @self.app.post("/upload", response_model=APIResponse)
        async def upload_file(
            file: bytes,
            filename: str,
            current_user: str = Depends(get_current_user)
        ):
            try:
                upload_dir = Path("uploads")
                upload_dir.mkdir(exist_ok=True)
                
                file_path = upload_dir / f"{current_user}_{filename}"
                
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(file)
                
                return APIResponse(
                    success=True,
                    data={
                        "filename": filename,
                        "size": len(file),
                        "path": str(file_path)
                    },
                    message="File uploaded successfully"
                )
                
            except Exception as e:
                logger.error(f"File upload failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Error handlers
        @self.app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "Endpoint not found",
                    "path": str(request.url.path)
                }
            )
        
        @self.app.exception_handler(500)
        async def internal_error_handler(request: Request, exc):
            logger.error(f"Internal server error: {exc}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal server error",
                    "error": str(exc) if self.config.get("debug", False) else "Internal error"
                }
            )

# FastAPI app factory
def create_api_gateway(config: Dict[str, Any] = None) -> FastAPI:
    """Create and configure API Gateway"""
    gateway = APIGateway(config)
    gateway._start_time = time.time()
    return gateway.app

# CLI for running the API Gateway
def run_api_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    workers: int = 1,
    config_file: str = None
):
    """Run the API Gateway server"""
    import uvicorn
    
    # Load configuration
    config = {}
    if config_file:
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    app = create_api_gateway(config)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=workers,
        access_log=True,
        log_level="info"
    )

# Example configuration
EXAMPLE_CONFIG = {
    "secret_key": "your-secret-key-here",
    "redis_url": "redis://localhost:6379",
    "allowed_origins": ["http://localhost:3000", "https://neuros.ai"],
    "rate_limit": {
        "requests_per_minute": 1000,
        "burst_size": 50,
        "window_size": 60
    },
    "debug": False
}

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        run_api_server(config_file=config_file)
    else:
        run_api_server()