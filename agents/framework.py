# neuros/agents/framework.py
"""
AI Agent Framework for neurOS
Intelligent agents for pipeline optimization, anomaly detection, and autonomous operation
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import numpy as np
import yaml
from datetime import datetime, timedelta

class AgentType(Enum):
    OPTIMIZER = "optimizer"
    ANOMALY_DETECTOR = "anomaly_detector"
    PIPELINE_GENERATOR = "pipeline_generator"
    PERFORMANCE_MONITOR = "performance_monitor"
    SECURITY_AGENT = "security_agent"

@dataclass
class AgentConfig:
    """Configuration for AI agents"""
    agent_type: AgentType
    name: str
    enabled: bool = True
    update_interval_seconds: int = 30
    learning_rate: float = 0.01
    confidence_threshold: float = 0.8
    max_iterations: int = 1000
    model_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentDecision:
    """Decision output from an agent"""
    agent_name: str
    decision_type: str
    confidence: float
    recommendations: List[Dict[str, Any]]
    reasoning: str
    timestamp: datetime
    data_used: Dict[str, Any] = field(default_factory=dict)

class BaseAgent(ABC):
    """Base class for all neurOS AI agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"neurOS.agent.{config.name}")
        self.is_running = False
        self.decisions_history = []
        self.performance_metrics = {}
        
    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> AgentDecision:
        """Analyze data and make decisions"""
        pass
    
    @abstractmethod
    async def learn(self, feedback: Dict[str, Any]) -> None:
        """Learn from feedback"""
        pass
    
    async def start(self):
        """Start the agent"""
        self.is_running = True
        self.logger.info(f"Agent {self.config.name} started")
    
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        self.logger.info(f"Agent {self.config.name} stopped")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return {
            'name': self.config.name,
            'type': self.config.agent_type.value,
            'decisions_made': len(self.decisions_history),
            'avg_confidence': np.mean([d.confidence for d in self.decisions_history]) if self.decisions_history else 0,
            'is_running': self.is_running,
            'last_decision': self.decisions_history[-1].timestamp if self.decisions_history else None
        }

class PipelineOptimizerAgent(BaseAgent):
    """Agent for optimizing BCI pipeline parameters"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.optimization_history = []
        self.parameter_bounds = {
            'bandpass_low': (0.5, 5.0),
            'bandpass_high': (40, 100),
            'notch_freq': (48, 52),
            'window_size': (0.5, 5.0),
            'overlap': (0.0, 0.9)
        }
        
    async def analyze(self, data: Dict[str, Any]) -> AgentDecision:
        """Analyze pipeline performance and suggest optimizations"""
        # Extract performance metrics
        latency = data.get('avg_latency_ms', 100)
        accuracy = data.get('classification_accuracy', 0.5)
        signal_quality = data.get('signal_quality', 0.5)
        
        # Simple optimization logic (in production, use more sophisticated ML)
        recommendations = []
        reasoning_parts = []
        confidence = 0.5
        
        # Latency optimization
        if latency > 100:
            recommendations.append({
                'parameter': 'window_size',
                'current_value': data.get('window_size', 2.0),
                'suggested_value': max(0.5, data.get('window_size', 2.0) * 0.8),
                'reasoning': 'Reduce window size to decrease latency'
            })
            reasoning_parts.append("High latency detected")
            confidence += 0.2
        
        # Accuracy optimization
        if accuracy < 0.7:
            recommendations.append({
                'parameter': 'bandpass_high',
                'current_value': data.get('bandpass_high', 40),
                'suggested_value': min(100, data.get('bandpass_high', 40) + 10),
                'reasoning': 'Increase upper frequency bound for better feature extraction'
            })
            reasoning_parts.append("Low accuracy requires frequency adjustment")
            confidence += 0.3
        
        # Signal quality optimization
        if signal_quality < 0.6:
            recommendations.append({
                'parameter': 'notch_freq',
                'current_value': data.get('notch_freq', 50),
                'suggested_value': 50,  # Standard power line frequency
                'reasoning': 'Apply notch filter to remove power line interference'
            })
            reasoning_parts.append("Poor signal quality detected")
            confidence += 0.2
        
        decision = AgentDecision(
            agent_name=self.config.name,
            decision_type="pipeline_optimization",
            confidence=min(confidence, 1.0),
            recommendations=recommendations,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No optimizations needed",
            timestamp=datetime.utcnow(),
            data_used={'latency': latency, 'accuracy': accuracy, 'signal_quality': signal_quality}
        )
        
        self.decisions_history.append(decision)
        return decision
    
    async def learn(self, feedback: Dict[str, Any]):
        """Learn from optimization results"""
        success = feedback.get('improvement', False)
        if success:
            self.logger.info("Optimization successful, updating parameters")
        else:
            self.logger.info("Optimization failed, reverting parameters")

class AnomalyDetectorAgent(BaseAgent):
    """Agent for detecting anomalies in BCI data and system performance"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.baseline_metrics = {}
        self.anomaly_threshold = 2.0  # Standard deviations
        
    async def analyze(self, data: Dict[str, Any]) -> AgentDecision:
        """Detect anomalies in system performance or signal quality"""
        anomalies = []
        reasoning_parts = []
        
        # Check various metrics for anomalies
        metrics_to_check = ['latency_ms', 'cpu_usage', 'memory_usage', 'signal_amplitude']
        
        for metric in metrics_to_check:
            if metric in data:
                current_value = data[metric]
                
                # Initialize baseline if not exists
                if metric not in self.baseline_metrics:
                    self.baseline_metrics[metric] = {'values': [current_value], 'mean': current_value, 'std': 0}
                    continue
                
                baseline = self.baseline_metrics[metric]
                deviation = abs(current_value - baseline['mean'])
                
                if baseline['std'] > 0 and deviation > self.anomaly_threshold * baseline['std']:
                    anomalies.append({
                        'metric': metric,
                        'current_value': current_value,
                        'baseline_mean': baseline['mean'],
                        'deviation_score': deviation / baseline['std'] if baseline['std'] > 0 else 0,
                        'severity': 'high' if deviation > 3 * baseline['std'] else 'medium'
                    })
                    reasoning_parts.append(f"{metric} anomaly detected")
                
                # Update baseline (exponential moving average)
                baseline['values'].append(current_value)
                if len(baseline['values']) > 100:
                    baseline['values'].pop(0)
                
                baseline['mean'] = np.mean(baseline['values'])
                baseline['std'] = np.std(baseline['values'])
        
        confidence = min(len(anomalies) * 0.3, 1.0) if anomalies else 0.1
        
        decision = AgentDecision(
            agent_name=self.config.name,
            decision_type="anomaly_detection",
            confidence=confidence,
            recommendations=[{
                'action': 'investigate_anomaly',
                'anomalies': anomalies,
                'suggested_actions': ['check_hardware', 'review_preprocessing', 'monitor_closely']
            }] if anomalies else [],
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No anomalies detected",
            timestamp=datetime.utcnow(),
            data_used=data
        )
        
        self.decisions_history.append(decision)
        return decision
    
    async def learn(self, feedback: Dict[str, Any]):
        """Learn from anomaly detection feedback"""
        false_positive = feedback.get('false_positive', False)
        if false_positive:
            # Adjust threshold to reduce false positives
            self.anomaly_threshold *= 1.1
            self.logger.info(f"Adjusted anomaly threshold to {self.anomaly_threshold}")

class PipelineGeneratorAgent(BaseAgent):
    """Agent for automatically generating BCI pipelines"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.pipeline_templates = {
            'motor_imagery': {
                'preprocessing': ['bandpass_filter', 'car', 'notch_filter'],
                'features': ['csp', 'bandpower'],
                'classifier': 'lda'
            },
            'p300': {
                'preprocessing': ['bandpass_filter', 'baseline_correction'],
                'features': ['time_domain', 'peak_detection'],
                'classifier': 'svm'
            },
            'ssvep': {
                'preprocessing': ['bandpass_filter', 'notch_filter'],
                'features': ['cca', 'fft'],
                'classifier': 'template_matching'
            }
        }
    
    async def analyze(self, data: Dict[str, Any]) -> AgentDecision:
        """Generate pipeline based on requirements"""
        task_type = data.get('task_type', 'motor_imagery')
        signal_type = data.get('signal_type', 'eeg')
        channels = data.get('channels', 32)
        sample_rate = data.get('sample_rate', 250)
        
        # Select appropriate template
        template = self.pipeline_templates.get(task_type, self.pipeline_templates['motor_imagery'])
        
        # Customize based on requirements
        pipeline_config = {
            'name': f"auto_generated_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'signal_type': signal_type,
            'channels': channels,
            'sample_rate': sample_rate,
            'preprocessing': template['preprocessing'].copy(),
            'features': template['features'].copy(),
            'classifier': template['classifier']
        }
        
        # Adaptive modifications
        if channels > 64:
            pipeline_config['preprocessing'].append('channel_selection')
        
        if sample_rate > 500:
            pipeline_config['preprocessing'].insert(0, 'downsample')
        
        recommendations = [{
            'action': 'create_pipeline',
            'pipeline_config': pipeline_config,
            'estimated_performance': self._estimate_performance(task_type, signal_type)
        }]
        
        confidence = 0.8 if task_type in self.pipeline_templates else 0.5
        
        decision = AgentDecision(
            agent_name=self.config.name,
            decision_type="pipeline_generation",
            confidence=confidence,
            recommendations=recommendations,
            reasoning=f"Generated {task_type} pipeline for {signal_type} with {channels} channels",
            timestamp=datetime.utcnow(),
            data_used=data
        )
        
        self.decisions_history.append(decision)
        return decision
    
    def _estimate_performance(self, task_type: str, signal_type: str) -> Dict[str, float]:
        """Estimate expected performance metrics"""
        base_performance = {
            'motor_imagery': {'accuracy': 0.75, 'latency_ms': 150},
            'p300': {'accuracy': 0.85, 'latency_ms': 200},
            'ssvep': {'accuracy': 0.90, 'latency_ms': 100}
        }
        
        performance = base_performance.get(task_type, {'accuracy': 0.7, 'latency_ms': 200})
        
        # Adjust for signal type
        if signal_type == 'ecog':
            performance['accuracy'] *= 1.15  # ECoG typically more accurate
            performance['latency_ms'] *= 0.8  # Lower latency
        
        return performance
    
    async def learn(self, feedback: Dict[str, Any]):
        """Learn from pipeline performance"""
        actual_performance = feedback.get('performance', {})
        pipeline_type = feedback.get('pipeline_type')
        
        if pipeline_type and actual_performance:
            self.logger.info(f"Learning from {pipeline_type} performance: {actual_performance}")

class AgentManager:
    """Manages all AI agents in neurOS"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("neurOS.agent_manager")
        self.is_running = False
        
    def register_agent(self, agent: BaseAgent):
        """Register a new agent"""
        self.agents[agent.config.name] = agent
        self.logger.info(f"Registered agent: {agent.config.name}")
    
    async def start_all_agents(self):
        """Start all registered agents"""
        for agent in self.agents.values():
            if agent.config.enabled:
                await agent.start()
        self.is_running = True
        self.logger.info("All agents started")
    
    async def stop_all_agents(self):
        """Stop all agents"""
        for agent in self.agents.values():
            await agent.stop()
        self.is_running = False
        self.logger.info("All agents stopped")
    
    async def get_recommendations(self, data: Dict[str, Any]) -> List[AgentDecision]:
        """Get recommendations from all active agents"""
        decisions = []
        
        for agent in self.agents.values():
            if agent.is_running:
                try:
                    decision = await agent.analyze(data)
                    if decision.confidence >= agent.config.confidence_threshold:
                        decisions.append(decision)
                except Exception as e:
                    self.logger.error(f"Agent {agent.config.name} error: {e}")
        
        return decisions
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {
            'total_agents': len(self.agents),
            'active_agents': sum(1 for agent in self.agents.values() if agent.is_running),
            'agents': {}
        }
        
        for name, agent in self.agents.items():
            status['agents'][name] = agent.get_metrics()
        
        return status
    
    async def provide_feedback(self, agent_name: str, feedback: Dict[str, Any]):
        """Provide feedback to specific agent"""
        if agent_name in self.agents:
            await self.agents[agent_name].learn(feedback)
        else:
            self.logger.warning(f"Unknown agent: {agent_name}")

# Factory functions for creating pre-configured agents
def create_default_agents() -> List[BaseAgent]:
    """Create default set of neurOS agents"""
    agents = []
    
    # Optimizer agent
    optimizer_config = AgentConfig(
        agent_type=AgentType.OPTIMIZER,
        name="pipeline_optimizer",
        update_interval_seconds=60,
        confidence_threshold=0.7
    )
    agents.append(PipelineOptimizerAgent(optimizer_config))
    
    # Anomaly detector
    anomaly_config = AgentConfig(
        agent_type=AgentType.ANOMALY_DETECTOR,
        name="anomaly_detector",
        update_interval_seconds=30,
        confidence_threshold=0.6
    )
    agents.append(AnomalyDetectorAgent(anomaly_config))
    
    # Pipeline generator
    generator_config = AgentConfig(
        agent_type=AgentType.PIPELINE_GENERATOR,
        name="pipeline_generator",
        update_interval_seconds=300,
        confidence_threshold=0.8
    )
    agents.append(PipelineGeneratorAgent(generator_config))
    
    return agents

# Example usage and testing
if __name__ == "__main__":
    async def test_agent_framework():
        # Create agent manager
        manager = AgentManager()
        
        # Register default agents
        for agent in create_default_agents():
            manager.register_agent(agent)
        
        # Start all agents
        await manager.start_all_agents()
        
        # Test data
        test_data = {
            'avg_latency_ms': 120,
            'classification_accuracy': 0.65,
            'signal_quality': 0.7,
            'cpu_usage': 85,
            'memory_usage': 70,
            'task_type': 'motor_imagery',
            'channels': 32,
            'sample_rate': 250
        }
        
        # Get recommendations
        decisions = await manager.get_recommendations(test_data)
        
        print("Agent Decisions:")
        for decision in decisions:
            print(f"\nAgent: {decision.agent_name}")
            print(f"Type: {decision.decision_type}")
            print(f"Confidence: {decision.confidence:.2f}")
            print(f"Reasoning: {decision.reasoning}")
            print(f"Recommendations: {len(decision.recommendations)}")
        
        # Get agent status
        status = manager.get_agent_status()
        print(f"\nAgent Status: {status['active_agents']}/{status['total_agents']} active")
        
        # Stop all agents
        await manager.stop_all_agents()
    
    # Run test
    asyncio.run(test_agent_framework())