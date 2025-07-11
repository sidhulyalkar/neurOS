# neuros/collaboration/realtime_system.py
"""
Real-time Collaboration System for neurOS
Multi-user real-time features with synchronized sessions
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager

import websockets
from websockets.server import WebSocketServerProtocol
import redis.asyncio as redis
from pydantic import BaseModel
import numpy as np

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of collaboration events"""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    PIPELINE_SHARED = "pipeline_shared"
    PIPELINE_UPDATED = "pipeline_updated"
    DATA_STREAMED = "data_streamed"
    ANNOTATION_ADDED = "annotation_added"
    CURSOR_MOVED = "cursor_moved"
    CHAT_MESSAGE = "chat_message"
    SYSTEM_NOTIFICATION = "system_notification"

class UserRole(Enum):
    """User roles in collaboration sessions"""
    VIEWER = "viewer"
    COLLABORATOR = "collaborator"
    MODERATOR = "moderator"
    OWNER = "owner"

@dataclass
class CollaborationUser:
    """User in a collaboration session"""
    user_id: str
    username: str
    role: UserRole
    connected_at: datetime
    last_activity: datetime
    cursor_position: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CollaborationEvent:
    """Collaboration event"""
    event_id: str
    event_type: EventType
    user_id: str
    session_id: str
    timestamp: datetime
    data: Dict[str, Any]
    targets: Optional[List[str]] = None  # Specific user targets

@dataclass
class SharedPipeline:
    """Shared pipeline in collaboration session"""
    pipeline_id: str
    name: str
    owner_id: str
    config: Dict[str, Any]
    permissions: Dict[str, UserRole] = field(default_factory=dict)
    version: int = 1
    last_modified: datetime = field(default_factory=datetime.now)

class CollaborationSession:
    """Real-time collaboration session"""
    
    def __init__(self, session_id: str, created_by: str, name: str = ""):
        self.session_id = session_id
        self.name = name or f"Session {session_id[:8]}"
        self.created_by = created_by
        self.created_at = datetime.now()
        
        self.users: Dict[str, CollaborationUser] = {}
        self.websockets: Dict[str, WebSocketServerProtocol] = {}
        self.shared_pipelines: Dict[str, SharedPipeline] = {}
        self.event_history: List[CollaborationEvent] = []
        self.annotations: List[Dict[str, Any]] = []
        
        self.max_users = 50
        self.is_active = True
        
    async def add_user(self, user: CollaborationUser, websocket: WebSocketServerProtocol):
        """Add user to session"""
        if len(self.users) >= self.max_users:
            raise ValueError("Session is full")
        
        self.users[user.user_id] = user
        self.websockets[user.user_id] = websocket
        
        # Broadcast user join event
        event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.USER_JOIN,
            user_id=user.user_id,
            session_id=self.session_id,
            timestamp=datetime.now(),
            data={
                "username": user.username,
                "role": user.role.value,
                "user_count": len(self.users)
            }
        )
        
        await self.broadcast_event(event, exclude_user=user.user_id)
        
        # Send session state to new user
        await self.send_session_state(user.user_id)
        
        logger.info(f"User {user.username} joined session {self.session_id}")
    
    async def remove_user(self, user_id: str):
        """Remove user from session"""
        if user_id not in self.users:
            return
        
        user = self.users[user_id]
        
        # Close websocket
        if user_id in self.websockets:
            try:
                await self.websockets[user_id].close()
            except:
                pass
            del self.websockets[user_id]
        
        del self.users[user_id]
        
        # Broadcast user leave event
        event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.USER_LEAVE,
            user_id=user_id,
            session_id=self.session_id,
            timestamp=datetime.now(),
            data={
                "username": user.username,
                "user_count": len(self.users)
            }
        )
        
        await self.broadcast_event(event)
        
        logger.info(f"User {user.username} left session {self.session_id}")
        
        # Close session if empty
        if not self.users:
            self.is_active = False
    
    async def broadcast_event(self, event: CollaborationEvent, exclude_user: str = None):
        """Broadcast event to all users in session"""
        self.event_history.append(event)
        
        # Keep only last 1000 events
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-1000:]
        
        message = {
            "type": "collaboration_event",
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }
        }
        
        # Send to specific targets or all users
        targets = event.targets or list(self.users.keys())
        if exclude_user:
            targets = [uid for uid in targets if uid != exclude_user]
        
        for user_id in targets:
            if user_id in self.websockets:
                try:
                    await self.websockets[user_id].send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    # Remove disconnected user
                    await self.remove_user(user_id)
                except Exception as e:
                    logger.error(f"Failed to send event to user {user_id}: {e}")
    
    async def send_session_state(self, user_id: str):
        """Send current session state to user"""
        if user_id not in self.websockets:
            return
        
        state = {
            "type": "session_state",
            "session": {
                "session_id": self.session_id,
                "name": self.name,
                "created_by": self.created_by,
                "created_at": self.created_at.isoformat(),
                "users": [
                    {
                        "user_id": u.user_id,
                        "username": u.username,
                        "role": u.role.value,
                        "connected_at": u.connected_at.isoformat(),
                        "cursor_position": u.cursor_position
                    }
                    for u in self.users.values()
                ],
                "shared_pipelines": [
                    {
                        "pipeline_id": p.pipeline_id,
                        "name": p.name,
                        "owner_id": p.owner_id,
                        "version": p.version,
                        "last_modified": p.last_modified.isoformat()
                    }
                    for p in self.shared_pipelines.values()
                ],
                "annotations": self.annotations[-50:]  # Last 50 annotations
            }
        }
        
        try:
            await self.websockets[user_id].send(json.dumps(state))
        except Exception as e:
            logger.error(f"Failed to send session state to user {user_id}: {e}")
    
    async def share_pipeline(self, pipeline: SharedPipeline, user_id: str):
        """Share a pipeline in the session"""
        self.shared_pipelines[pipeline.pipeline_id] = pipeline
        
        event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.PIPELINE_SHARED,
            user_id=user_id,
            session_id=self.session_id,
            timestamp=datetime.now(),
            data={
                "pipeline_id": pipeline.pipeline_id,
                "name": pipeline.name,
                "owner_id": pipeline.owner_id
            }
        )
        
        await self.broadcast_event(event)
    
    async def update_pipeline(self, pipeline_id: str, updates: Dict[str, Any], user_id: str):
        """Update shared pipeline"""
        if pipeline_id not in self.shared_pipelines:
            return
        
        pipeline = self.shared_pipelines[pipeline_id]
        
        # Check permissions
        user_role = pipeline.permissions.get(user_id, UserRole.VIEWER)
        if user_role == UserRole.VIEWER:
            return
        
        # Apply updates
        pipeline.config.update(updates)
        pipeline.version += 1
        pipeline.last_modified = datetime.now()
        
        event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.PIPELINE_UPDATED,
            user_id=user_id,
            session_id=self.session_id,
            timestamp=datetime.now(),
            data={
                "pipeline_id": pipeline_id,
                "updates": updates,
                "version": pipeline.version
            }
        )
        
        await self.broadcast_event(event, exclude_user=user_id)
    
    async def add_annotation(self, annotation: Dict[str, Any], user_id: str):
        """Add annotation to session"""
        annotation.update({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id
        })
        
        self.annotations.append(annotation)
        
        event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.ANNOTATION_ADDED,
            user_id=user_id,
            session_id=self.session_id,
            timestamp=datetime.now(),
            data={"annotation": annotation}
        )
        
        await self.broadcast_event(event, exclude_user=user_id)

class CollaborationManager:
    """Manager for collaboration sessions"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.sessions: Dict[str, CollaborationSession] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.redis_url = redis_url
        self.redis_client = None
        
    async def initialize(self):
        """Initialize collaboration manager"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Collaboration manager initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            logger.info("Running collaboration manager without Redis")
    
    async def create_session(self, created_by: str, name: str = "") -> str:
        """Create new collaboration session"""
        session_id = str(uuid.uuid4())
        session = CollaborationSession(session_id, created_by, name)
        
        self.sessions[session_id] = session
        
        # Store in Redis if available
        if self.redis_client:
            await self.redis_client.hset(
                "neuros:sessions",
                session_id,
                json.dumps({
                    "created_by": created_by,
                    "name": name,
                    "created_at": session.created_at.isoformat()
                })
            )
        
        logger.info(f"Created collaboration session {session_id}")
        return session_id
    
    async def join_session(
        self,
        session_id: str,
        user_id: str,
        username: str,
        role: UserRole,
        websocket: WebSocketServerProtocol
    ) -> bool:
        """Join collaboration session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Remove user from previous session
        if user_id in self.user_sessions:
            old_session_id = self.user_sessions[user_id]
            if old_session_id in self.sessions:
                await self.sessions[old_session_id].remove_user(user_id)
        
        user = CollaborationUser(
            user_id=user_id,
            username=username,
            role=role,
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        try:
            await session.add_user(user, websocket)
            self.user_sessions[user_id] = session_id
            return True
        except Exception as e:
            logger.error(f"Failed to join session {session_id}: {e}")
            return False
    
    async def leave_session(self, user_id: str):
        """Leave current session"""
        if user_id not in self.user_sessions:
            return
        
        session_id = self.user_sessions[user_id]
        if session_id in self.sessions:
            await self.sessions[session_id].remove_user(user_id)
        
        del self.user_sessions[user_id]
    
    async def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get collaboration session"""
        return self.sessions.get(session_id)
    
    async def handle_message(self, user_id: str, message: Dict[str, Any]):
        """Handle message from user"""
        if user_id not in self.user_sessions:
            return
        
        session_id = self.user_sessions[user_id]
        session = self.sessions.get(session_id)
        if not session:
            return
        
        message_type = message.get("type")
        
        if message_type == "cursor_move":
            # Update user cursor position
            if user_id in session.users:
                session.users[user_id].cursor_position = message.get("position", {})
                session.users[user_id].last_activity = datetime.now()
                
                event = CollaborationEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.CURSOR_MOVED,
                    user_id=user_id,
                    session_id=session_id,
                    timestamp=datetime.now(),
                    data={"position": message.get("position", {})}
                )
                
                await session.broadcast_event(event, exclude_user=user_id)
        
        elif message_type == "chat_message":
            # Handle chat message
            chat_data = {
                "message": message.get("message", ""),
                "username": session.users[user_id].username if user_id in session.users else "Unknown"
            }
            
            event = CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.CHAT_MESSAGE,
                user_id=user_id,
                session_id=session_id,
                timestamp=datetime.now(),
                data=chat_data
            )
            
            await session.broadcast_event(event)
        
        elif message_type == "share_pipeline":
            # Share pipeline
            pipeline_data = message.get("pipeline", {})
            pipeline = SharedPipeline(
                pipeline_id=pipeline_data.get("id", str(uuid.uuid4())),
                name=pipeline_data.get("name", "Untitled Pipeline"),
                owner_id=user_id,
                config=pipeline_data.get("config", {})
            )
            
            await session.share_pipeline(pipeline, user_id)
        
        elif message_type == "update_pipeline":
            # Update pipeline
            pipeline_id = message.get("pipeline_id")
            updates = message.get("updates", {})
            
            await session.update_pipeline(pipeline_id, updates, user_id)
        
        elif message_type == "add_annotation":
            # Add annotation
            annotation = message.get("annotation", {})
            await session.add_annotation(annotation, user_id)
        
        elif message_type == "stream_data":
            # Stream real-time data
            data = message.get("data", {})
            
            event = CollaborationEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.DATA_STREAMED,
                user_id=user_id,
                session_id=session_id,
                timestamp=datetime.now(),
                data=data
            )
            
            await session.broadcast_event(event, exclude_user=user_id)
    
    async def cleanup_inactive_sessions(self):
        """Cleanup inactive sessions"""
        current_time = datetime.now()
        inactive_sessions = []
        
        for session_id, session in self.sessions.items():
            if not session.is_active:
                inactive_sessions.append(session_id)
                continue
            
            # Check for inactive users
            inactive_users = []
            for user_id, user in session.users.items():
                if current_time - user.last_activity > timedelta(minutes=30):
                    inactive_users.append(user_id)
            
            # Remove inactive users
            for user_id in inactive_users:
                await session.remove_user(user_id)
        
        # Remove inactive sessions
        for session_id in inactive_sessions:
            del self.sessions[session_id]
            if self.redis_client:
                await self.redis_client.hdel("neuros:sessions", session_id)
            logger.info(f"Cleaned up inactive session {session_id}")

class CollaborationWebSocketHandler:
    """WebSocket handler for collaboration"""
    
    def __init__(self, collaboration_manager: CollaborationManager):
        self.collaboration_manager = collaboration_manager
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        try:
            # Extract session_id and user info from path or initial message
            await websocket.send(json.dumps({
                "type": "connection_established",
                "message": "Please provide authentication and session info"
            }))
            
            # Wait for authentication message
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            user_id = auth_data.get("user_id")
            username = auth_data.get("username")
            session_id = auth_data.get("session_id")
            role = UserRole(auth_data.get("role", "viewer"))
            
            if not all([user_id, username, session_id]):
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Missing required authentication data"
                }))
                return
            
            # Join session
            success = await self.collaboration_manager.join_session(
                session_id, user_id, username, role, websocket
            )
            
            if not success:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Failed to join session"
                }))
                return
            
            await websocket.send(json.dumps({
                "type": "joined_session",
                "session_id": session_id,
                "user_id": user_id
            }))
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.collaboration_manager.handle_message(user_id, data)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON message received")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Clean up user session
            if 'user_id' in locals():
                await self.collaboration_manager.leave_session(user_id)

# FastAPI integration
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

def add_collaboration_routes(app: FastAPI, collaboration_manager: CollaborationManager):
    """Add collaboration routes to FastAPI app"""
    
    @app.websocket("/ws/collaborate")
    async def websocket_collaboration(websocket: WebSocket):
        await websocket.accept()
        
        handler = CollaborationWebSocketHandler(collaboration_manager)
        await handler.handle_connection(websocket, "/ws/collaborate")
    
    @app.post("/collaboration/sessions")
    async def create_collaboration_session(
        created_by: str,
        name: str = ""
    ):
        session_id = await collaboration_manager.create_session(created_by, name)
        return {
            "success": True,
            "session_id": session_id,
            "name": name
        }
    
    @app.get("/collaboration/sessions/{session_id}")
    async def get_collaboration_session(session_id: str):
        session = await collaboration_manager.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        return {
            "success": True,
            "session": {
                "session_id": session.session_id,
                "name": session.name,
                "created_by": session.created_by,
                "created_at": session.created_at.isoformat(),
                "user_count": len(session.users),
                "pipeline_count": len(session.shared_pipelines),
                "is_active": session.is_active
            }
        }
    
    @app.get("/collaboration/demo")
    async def collaboration_demo():
        """Demo page for collaboration features"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>neurOS Collaboration Demo</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 800px; margin: 0 auto; }
                .messages { height: 300px; border: 1px solid #ccc; overflow-y: auto; padding: 10px; margin: 10px 0; }
                .input-group { margin: 10px 0; }
                .input-group input, .input-group button { margin: 5px; padding: 8px; }
                .user-list { background: #f5f5f5; padding: 10px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🧠 neurOS Real-time Collaboration Demo</h1>
                
                <div class="input-group">
                    <input type="text" id="username" placeholder="Enter username" />
                    <input type="text" id="sessionId" placeholder="Enter session ID" />
                    <button onclick="connect()">Connect</button>
                    <button onclick="disconnect()">Disconnect</button>
                </div>
                
                <div class="user-list">
                    <h3>Connected Users:</h3>
                    <div id="userList"></div>
                </div>
                
                <div class="messages" id="messages"></div>
                
                <div class="input-group">
                    <input type="text" id="chatInput" placeholder="Type a message..." />
                    <button onclick="sendMessage()">Send</button>
                </div>
                
                <div class="input-group">
                    <button onclick="shareMockPipeline()">Share Mock Pipeline</button>
                    <button onclick="streamMockData()">Stream Mock Data</button>
                </div>
            </div>
            
            <script>
                let ws = null;
                let connected = false;
                
                function connect() {
                    const username = document.getElementById('username').value;
                    const sessionId = document.getElementById('sessionId').value;
                    
                    if (!username || !sessionId) {
                        alert('Please enter username and session ID');
                        return;
                    }
                    
                    ws = new WebSocket('ws://localhost:8000/ws/collaborate');
                    
                    ws.onopen = function() {
                        // Send authentication
                        ws.send(JSON.stringify({
                            user_id: username + '_' + Date.now(),
                            username: username,
                            session_id: sessionId,
                            role: 'collaborator'
                        }));
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        handleMessage(data);
                    };
                    
                    ws.onclose = function() {
                        connected = false;
                        addMessage('Disconnected from session');
                    };
                    
                    ws.onerror = function(error) {
                        addMessage('Connection error: ' + error);
                    };
                }
                
                function disconnect() {
                    if (ws) {
                        ws.close();
                    }
                }
                
                function handleMessage(data) {
                    switch(data.type) {
                        case 'joined_session':
                            connected = true;
                            addMessage('Connected to session: ' + data.session_id);
                            break;
                        case 'session_state':
                            updateUserList(data.session.users);
                            addMessage('Session state received');
                            break;
                        case 'collaboration_event':
                            handleCollaborationEvent(data.event);
                            break;
                        case 'error':
                            addMessage('Error: ' + data.message);
                            break;
                    }
                }
                
                function handleCollaborationEvent(event) {
                    switch(event.event_type) {
                        case 'user_join':
                            addMessage(event.data.username + ' joined the session');
                            break;
                        case 'user_leave':
                            addMessage(event.data.username + ' left the session');
                            break;
                        case 'chat_message':
                            addMessage(event.data.username + ': ' + event.data.message);
                            break;
                        case 'pipeline_shared':
                            addMessage('Pipeline shared: ' + event.data.name);
                            break;
                        case 'data_streamed':
                            addMessage('Data streamed: ' + JSON.stringify(event.data).substring(0, 50) + '...');
                            break;
                    }
                }
                
                function updateUserList(users) {
                    const userList = document.getElementById('userList');
                    userList.innerHTML = users.map(user => 
                        `<span style="margin-right: 10px;">${user.username} (${user.role})</span>`
                    ).join('');
                }
                
                function addMessage(message) {
                    const messages = document.getElementById('messages');
                    const timestamp = new Date().toLocaleTimeString();
                    messages.innerHTML += `<div>[${timestamp}] ${message}</div>`;
                    messages.scrollTop = messages.scrollHeight;
                }
                
                function sendMessage() {
                    const input = document.getElementById('chatInput');
                    const message = input.value.trim();
                    
                    if (!message || !connected) return;
                    
                    ws.send(JSON.stringify({
                        type: 'chat_message',
                        message: message
                    }));
                    
                    input.value = '';
                }
                
                function shareMockPipeline() {
                    if (!connected) return;
                    
                    ws.send(JSON.stringify({
                        type: 'share_pipeline',
                        pipeline: {
                            name: 'Mock BCI Pipeline',
                            config: {
                                sampling_rate: 250,
                                channels: 8,
                                filters: ['bandpass', 'notch']
                            }
                        }
                    }));
                }
                
                function streamMockData() {
                    if (!connected) return;
                    
                    const mockData = {
                        timestamp: new Date().toISOString(),
                        channels: 8,
                        samples: Array.from({length: 100}, () => Math.random() * 2 - 1)
                    };
                    
                    ws.send(JSON.stringify({
                        type: 'stream_data',
                        data: mockData
                    }));
                }
                
                // Handle enter key in chat input
                document.getElementById('chatInput').addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

# Background tasks
async def collaboration_cleanup_task(collaboration_manager: CollaborationManager):
    """Background task for cleaning up inactive sessions"""
    while True:
        try:
            await collaboration_manager.cleanup_inactive_sessions()
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute

# Usage example
async def main():
    """Example usage of collaboration system"""
    
    # Initialize collaboration manager
    collaboration_manager = CollaborationManager()
    await collaboration_manager.initialize()
    
    # Start cleanup task
    cleanup_task = asyncio.create_task(
        collaboration_cleanup_task(collaboration_manager)
    )
    
    # Create FastAPI app with collaboration
    app = FastAPI(title="neurOS Collaboration API")
    add_collaboration_routes(app, collaboration_manager)
    
    # Run server
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    finally:
        cleanup_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())