from agents.base_agent import Agent
import pytest
import json

class TestAgent(Agent):
    """
    Agent to generate and run tests for new features using an LLM model.
    It utilizes the base Agent's capabilities for interacting with the model.
    """

    def __init__(self, model_name: str = "gpt-4", temperature: float = 0.0, client=None):
        super().__init__(catalog=None, model_name=model_name, temperature=temperature, client=client)
    
    def generate_test(self, feature_code: str) -> str:
        """
        Generate a test case for the given feature code using LLM.
        :param feature_code: String representation of the feature code to be tested.
        :return: Generated test code as a string.
        """
        prompt = f"Generate a pytest unit test for the following Python feature:\n```python\n{feature_code}\n```\n"
        response = self._chat([
            {"role": "system", "content": "You are an expert Python developer specialized in testing."},
            {"role": "user", "content": prompt}
        ])
        return response

    def run_generated_test(self, test_code: str):
        """
        Run the generated test code.
        :param test_code: String representation of the test code to be executed.
        """
        with open("temp_test.py", "w") as f:
            f.write(test_code)
        
        # Execute the test using pytest
        result = pytest.main(["temp_test.py"])
        
        # Clean up
        import os
        os.remove("temp_test.py")
        
        return result
