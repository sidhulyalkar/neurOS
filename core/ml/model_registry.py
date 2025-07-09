# core/ml/model_registry.py
from typing import Protocol
import torch
import tensorflow as tf
from abc import ABC, abstractmethod

class BCIModel(Protocol):
    """Protocol for BCI models"""
    
    def predict(self, data: np.ndarray) -> np.ndarray:
        """Make predictions"""
        ...
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get model metadata"""
        ...

class ModelRegistry:
    """Central registry for ML models"""
    
    def __init__(self):
        self._models: Dict[str, BCIModel] = {}
        self._model_store = ModelStore()
        
    async def register_model(
        self,
        name: str,
        model: BCIModel,
        metadata: Dict[str, Any]
    ) -> str:
        """Register a new model"""
        model_id = f"{name}:{metadata['version']}"
        
        # Validate model
        await self._validate_model(model, metadata)
        
        # Store model
        storage_path = await self._model_store.save(model_id, model)
        
        # Register
        self._models[model_id] = model
        
        # Emit event
        await self._emit_event("model_registered", {
            "model_id": model_id,
            "metadata": metadata,
            "storage_path": storage_path
        })
        
        return model_id
        
    async def load_model(self, model_id: str) -> BCIModel:
        """Load model by ID"""
        if model_id in self._models:
            return self._models[model_id]
            
        # Load from storage
        model = await self._model_store.load(model_id)
        self._models[model_id] = model
        
        return model