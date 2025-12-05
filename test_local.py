from src.agent.core import MetadataAgent
from dotenv import load_dotenv

load_dotenv()

# Inicializar agente
agent = MetadataAgent()
agent.set_up()

# Ejecutar consulta
response = agent.query("Lista los archivos en el bucket y sugiere una descripción para el primero que encuentres.")
print(response)