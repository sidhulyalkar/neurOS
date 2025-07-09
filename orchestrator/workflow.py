# core/orchestrator/workflow.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum

class NodeType(str, Enum):
    DEVICE = "device"
    PROCESSOR = "processor"
    FEATURE = "feature"
    MODEL = "model"
    LLM = "llm"
    OUTPUT = "output"

class WorkflowNode(BaseModel):
    """Node in processing workflow"""
    id: str
    type: NodeType
    config: Dict[str, Any]
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)

class Workflow(BaseModel):
    """Complete workflow specification"""
    name: str
    version: str = "1.0"
    nodes: Dict[str, WorkflowNode]
    edges: list[tuple[str, str]]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkflowEngine:
    """Execute workflows"""
    
    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self._node_handlers: Dict[NodeType, Callable] = {
            NodeType.DEVICE: self._handle_device,
            NodeType.PROCESSOR: self._handle_processor,
            NodeType.LLM: self._handle_llm,
            # ... other handlers
        }
        
    async def execute(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute a workflow"""
        # Topological sort
        execution_order = self._topological_sort(workflow)
        
        # Execute nodes
        results = {}
        for node_id in execution_order:
            node = workflow.nodes[node_id]
            handler = self._node_handlers[node.type]
            
            # Gather inputs
            inputs = {inp: results[inp] for inp in node.inputs}
            
            # Execute node
            output = await handler(node, inputs)
            results[node_id] = output
            
        return results