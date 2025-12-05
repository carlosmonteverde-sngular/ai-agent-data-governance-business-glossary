# Guía de Ejecución: Agente de Metadatos Dataplex

Este documento describe cómo configurar, probar y desplegar el Agente de Metadatos en Vertex AI Reasoning Engine.

## 1. Prerrequisitos

Asegúrate de tener instalado:
- Python 3.10+
- Google Cloud SDK (`gcloud`)

### Configuración de Entorno

1. **Autenticación en GCP**:
   ```bash
   gcloud auth application-default login
   gcloud config set project TU_PROJECT_ID
   ```

2. **Entorno Virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Variables de Entorno**:
   Crea un archivo `.env` en la raíz del proyecto o exporta las variables:
   ```bash
   export PROJECT_ID="tu-project-id"
   export LOCATION="us-central1"
   export GCS_BUCKET="nombre-de-tu-bucket-gcs"
   ```

## 2. Ejecución Local (Pruebas)

Antes de desplegar, puedes probar la lógica del agente localmente. Esto inicializará el agente y ejecutará una consulta de prueba.

Crea un script temporal `test_local.py`:

```python
from src.agent.core import MetadataAgent
from dotenv import load_dotenv

load_dotenv()

# Inicializar agente
agent = MetadataAgent()
agent.set_up()

# Ejecutar consulta
response = agent.query("Lista los archivos en el bucket y sugiere una descripción para el primero que encuentres.")
print(response)
```

Ejecuta el script:
```bash
python test_local.py
```

## 3. Despliegue en Vertex AI Reasoning Engine

Para desplegar el agente como un servicio gestionado:

1. Ejecuta el script de despliegue:
   ```bash
   python scripts/deploy.py
   ```

2. El script imprimirá el `resource_name` del agente desplegado (ej. `projects/.../locations/.../reasoningEngines/...`).

## 4. Uso del Agente Desplegado

Una vez desplegado, puedes invocarlo desde cualquier aplicación usando el SDK de Vertex AI:

```python
from vertexai.preview import reasoning_engines

# Reemplaza con el ID retornado en el paso anterior
remote_agent = reasoning_engines.ReasoningEngine("projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/YOUR_AGENT_ID")

response = remote_agent.query(input="Analiza el archivo data_spec.pdf y actualiza la entrada correspondiente en Dataplex.")
print(response)
```
