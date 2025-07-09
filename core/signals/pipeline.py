# core/signals/pipeline.py
from typing import Protocol, TypeVar, Generic
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json

T = TypeVar('T')

class SignalProcessor(Protocol[T]):
    """Protocol for signal processors"""
    
    def process(self, data: np.ndarray, context: T) -> tuple[np.ndarray, Dict[str, Any]]:
        """Process signal data"""
        ...
        
    @property
    def latency_ms(self) -> float:
        """Expected processing latency"""
        ...

class ProcessingNode:
    """Node in processing graph"""
    
    def __init__(self, processor: SignalProcessor, name: str):
        self.processor = processor
        self.name = name
        self.inputs: List['ProcessingNode'] = []
        self.outputs: List['ProcessingNode'] = []
        self._cache = {}
        self._metrics = {}
        
    async def execute(self, inputs: Dict[str, np.ndarray], context: Any) -> np.ndarray:
        """Execute processing node"""
        # Get input data
        if len(self.inputs) == 1:
            input_data = inputs[self.inputs[0].name]
        else:
            # Merge multiple inputs
            input_data = self._merge_inputs(inputs)
            
        # Check cache
        cache_key = self._compute_cache_key(input_data, context)
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Process
        start_time = asyncio.get_event_loop().time()
        output, metrics = self.processor.process(input_data, context)
        
        # Update metrics
        self._metrics = {
            **metrics,
            "latency_ms": (asyncio.get_event_loop().time() - start_time) * 1000,
            "timestamp": datetime.utcnow()
        }
        
        # Cache result
        self._cache[cache_key] = output
        
        return output

class ProcessingGraph:
    """DAG of processing nodes"""
    
    def __init__(self):
        self.nodes: Dict[str, ProcessingNode] = {}
        self.edges: List[tuple[str, str]] = []
        self._execution_order: Optional[List[str]] = None
        
    def add_node(self, name: str, processor: SignalProcessor) -> 'ProcessingGraph':
        """Add processing node"""
        self.nodes[name] = ProcessingNode(processor, name)
        self._execution_order = None  # Invalidate cache
        return self
        
    def add_edge(self, from_node: str, to_node: str) -> 'ProcessingGraph':
        """Add edge between nodes"""
        self.edges.append((from_node, to_node))
        self.nodes[to_node].inputs.append(self.nodes[from_node])
        self.nodes[from_node].outputs.append(self.nodes[to_node])
        self._execution_order = None
        return self
        
    async def execute(self, input_data: np.ndarray, context: Any) -> Dict[str, np.ndarray]:
        """Execute processing graph"""
        if self._execution_order is None:
            self._execution_order = self._topological_sort()
            
        results = {"input": input_data}
        
        for node_name in self._execution_order:
            node = self.nodes[node_name]
            results[node_name] = await node.execute(results, context)
            
        return results
        
    def _topological_sort(self) -> List[str]:
        """Topological sort of processing nodes"""
        visited = set()
        stack = []
        
        def visit(node_name: str):
            if node_name in visited:
                return
            visited.add(node_name)
            
            node = self.nodes[node_name]
            for output in node.outputs:
                visit(output.name)
                
            stack.append(node_name)
            
        for node_name in self.nodes:
            visit(node_name)
            
        return stack[::-1]