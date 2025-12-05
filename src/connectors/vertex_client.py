import vertexai
from vertexai.generative_models import GenerativeModel

class VertexClient:
    def __init__(self, project_id: str, location: str):
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel("gemini-1.5-pro-001")

    def generate_content(self, prompt: str) -> str:
        """Generates content using Gemini."""
        response = self.model.generate_content(prompt)
        return response.text
