# core/agents/orchestrator.py
"""
Enhanced Agent Orchestrator for neurOS
Manages coordination between AI agents
"""

import asyncio
from typing import Dict, Any, List

class AgentOrchestrator:
    """Orchestrates multiple AI agents"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.workflows: Dict[str, List[str]] = {}
        
    async def initialize(self):
        """Initialize orchestrator"""
        # Register default agents from existing codebase
        try:
            from agents.spec_agent import SpecAgent
            from agents.code_agent import CodeAgent
            from agents.feature_agent import FeatureAgent
            
            self.agents["spec"] = SpecAgent()
            self.agents["code"] = CodeAgent()
            if FeatureAgent:
                self.agents["feature"] = FeatureAgent()
        except ImportError:
            print("Some agents not available yet - will load when available")
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data through agent workflow"""
        results = {}
        
        # Simple sequential processing
        for agent_name, agent in self.agents.items():
            if hasattr(agent, 'process'):
                try:
                    agent_result = await agent.process(data)
                    results[f"{agent_name}_result"] = agent_result
                except:
                    results[f"{agent_name}_result"] = f"Agent {agent_name} processing skipped"
                
        return results
        
    def register_agent(self, name: str, agent: Any):
        """Register new agent"""
        self.agents[name] = agent
        
    def register_workflow(self, name: str, agent_sequence: List[str]):
        """Register agent workflow"""
        self.workflows[name] = agent_sequence
