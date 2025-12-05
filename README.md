# Dataplex Metadata Agent

Agente de IA para automatizar la gestión de metadatos y reglas de calidad en Google Cloud Dataplex.

## Descripción
Este proyecto implementa un agente que utiliza Vertex AI (Gemini) para analizar documentación desestructurada (PDFs en GCS) y metadatos existentes en Dataplex para sugerir enriquecimientos de metadatos y reglas de calidad de datos.

## Estructura
- `src/agent`: Lógica del agente y orquestación.
- `src/connectors`: Clientes para GCS, Dataplex y Vertex AI.
- `src/models`: Modelos de datos (Pydantic).

## Setup
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Configurar credenciales de GCP (Application Default Credentials):
   ```bash
   gcloud auth application-default login
   ```
3. Configurar variables de entorno (ver `config/`).

## Uso
(Pendiente de implementación)
