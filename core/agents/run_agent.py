# agents/run_agent.py
from .. import pipeline 

class RunAgent:
    def run(self, workflow_path: str):
        """
        Executes the core NeuroForge pipeline.
        """
        result = pipeline.run_full_pipeline(workflow_path)
        
        # Write the raw and cleaned EEG data to the Neuralake catalog
        BCI_CATALOG.db("bci").table(RAW_EEG).write(result["raw"])
        BCI_CATALOG.db("bci").table(cleaned_eeg).write(result["clean"])
        
        # Compute features from the cleaned EEG and store them in the catalog
        feature_agent = FeatureAgent()
        features_df = feature_agent.run(result["clean"])
        BCI_CATALOG.db("bci").table(features).write(features_df)
        
        # Train a decoding model on the features
        train_agent = TrainAgent()
        model = train_agent.run(features_df)
        
        # Make predictions on the raw EEG data
        inference_agent = InferenceAgent()
        predictions = inference_agent.run(model, result["raw"])
        
        # Store the predictions in the catalog
        BCI_CATALOG.db("bci").table("predictions").write(predictions)
        
        return result


