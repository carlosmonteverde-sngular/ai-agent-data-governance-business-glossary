from vertexai.preview import reasoning_engines
from src.agent.tools import DataplexTools

class MetadataAgent:
    def __init__(self):
        self.tools = DataplexTools()
        self.model = "gemini-1.5-pro-001"

    def set_up(self):
        """Sets up the agent with tools and model."""
        # This method is called by Reasoning Engine during initialization
        # We define the agent using LangChain or Vertex AI SDK
        from langchain_google_vertexai import ChatVertexAI
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate
        from langchain.tools import tool

        # Wrap methods as tools
        @tool
        def list_files(prefix: str = None):
            """Lists files in GCS."""
            return self.tools.list_gcs_files(prefix)

        @tool
        def read_file(file_name: str):
            """Reads a file from GCS."""
            return self.tools.read_gcs_file(file_name)

        @tool
        def update_entry(entry_name: str, description: str):
            """Updates Dataplex entry description."""
            return self.tools.update_dataplex_entry_description(entry_name, description)

        self.defined_tools = [list_files, read_file, update_entry]
        
        llm = ChatVertexAI(model_name=self.model)
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a Dataplex Metadata Agent. Your goal is to analyze files in GCS and update Dataplex metadata."),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )

        agent = create_tool_calling_agent(llm, self.defined_tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.defined_tools, verbose=True)

    def query(self, input: str):
        """Queries the agent."""
        return self.agent_executor.invoke({"input": input})

