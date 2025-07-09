# apps/marketplace/app_store.py
class NeuralAppStore:
    """Marketplace for BCI applications"""
    
    def __init__(self):
        self.registry = AppRegistry()
        self.validator = AppValidator()
        self.monetization = MonetizationEngine()
        
    async def submit_app(
        self,
        developer_id: str,
        app_package: bytes
    ) -> str:
        """Submit app for review"""
        # Validate package
        validation_result = await self.validator.validate(app_package)
        
        if not validation_result.passed:
            raise ValidationError(validation_result.errors)
            
        # Extract metadata
        metadata = await self._extract_metadata(app_package)
        
        # Create submission
        submission_id = await self.registry.create_submission(
            developer_id=developer_id,
            metadata=metadata,
            package=app_package
        )
        
        # Start review process
        await self._start_review(submission_id)
        
        return submission_id
        
    async def install_app(
        self,
        user_id: str,
        app_id: str
    ) -> Installation:
        """Install app for user"""
        # Check purchase
        if not await self.monetization.check_purchase(user_id, app_id):
            # Process payment
            await self.monetization.process_purchase(user_id, app_id)
            
        # Download package
        package = await self.registry.download_package(app_id)
        
        # Install
        installation = await self._install_package(user_id, package)
        
        return installation