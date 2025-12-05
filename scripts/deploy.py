import os
import sys

# Add project root to sys.path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.core import MetadataAgent
from vertexai.preview import reasoning_engines
from src.utils.config import PROJECT_ID, LOCATION, GCS_BUCKET

def deploy():
    print(f"Deploying Agent to {LOCATION}...")
    
    # Initialize the agent locally to verify
    agent = MetadataAgent()
    
    # Deploy to Vertex AI Reasoning Engine
    remote_agent = reasoning_engines.ReasoningEngine.create(
        MetadataAgent(),
        requirements=[
            "google-cloud-dataplex",
            "google-cloud-storage",
            "google-cloud-aiplatform[reasoningengine]",
            "langchain",
            "langchain-google-vertexai",
            "pydantic",
            "python-dotenv"
        ],
        display_name="dataplex-metadata-agent",
        description="Agent to automate Dataplex metadata and quality rules.",
        sys_version="3.10",
    )
    
    print(f"Agent deployed: {remote_agent.resource_name}")
    return remote_agent

if __name__ == "__main__":
    deploy()
