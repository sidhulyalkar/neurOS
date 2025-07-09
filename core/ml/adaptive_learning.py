# core/ml/adaptive_learning.py
class AdaptiveLearning:
    """Online learning and model adaptation"""
    
    def __init__(self, base_model: BCIModel):
        self.base_model = base_model
        self.adaptation_buffer = []
        self.performance_metrics = []
        
    async def update(self, data: np.ndarray, feedback: Any):
        """Update model with new data"""
        # Add to buffer
        self.adaptation_buffer.append((data, feedback))
        
        # Check if update needed
        if len(self.adaptation_buffer) >= self.batch_size:
            await self._adapt_model()
            
    async def _adapt_model(self):
        """Perform model adaptation"""
        # Convert buffer to training batch
        X, y = self._prepare_batch(self.adaptation_buffer)
        
        # Fine-tune model
        if hasattr(self.base_model, 'partial_fit'):
            self.base_model.partial_fit(X, y)
        else:
            # Use meta-learning approach
            await self._meta_learning_update(X, y)
            
        # Clear buffer
        self.adaptation_buffer.clear()