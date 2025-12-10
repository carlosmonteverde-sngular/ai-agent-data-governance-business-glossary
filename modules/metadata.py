from core.vertex_client import VertexAIClient


class MetadataEnricher:
    def __init__(self, ai_client: VertexAIClient):
        self.ai_client = ai_client

    def suggest_metadata(self, gcs_uri: str, existing_metadata_context: str) -> str:
        """
        Analyze existing document + metadata to suggest improvements.
        """
        # TODO: Revisar prompt
        prompt = f"""
        TU ROL: Actúa como un Data Steward experto. 

        TIENES DOS FUENTES DE INFORMACIÓN:
        1. El documento PDF adjunto (Documentación técnica/negocio).
        2. Los metadatos técnicos actuales extraídos de Dataplex:
           --- INICIO METADATOS ACTUALES ---
           {existing_metadata_context}
           --- FIN METADATOS ACTUALES ---

        TU OBJETIVO:
        Eres un agente de metadatos de Dataplex, analiza si la definición actual en Dataplex coincide con la documentación del PDF.
        Genera un JSON con sugerencias de enriquecimiento:

        1. "metadata_update": Incluye una lista con los metadatos mejorados si procede.
        2. "missing_fields": Lista campos mencionados en el PDF que NO aparecen en el esquema actual de Dataplex.
        3. "business_domain": Dominio de negocio inferido.
        4. "data_quality_flag": "RED" si detectas contradicciones graves entre el PDF y el esquema actual, "GREEN" si es consistente.

        Responde ÚNICAMENTE con el bloque JSON.
        """

        print(f"--- Initiating cross-analysis (PDF vs Dataplex) to: {gcs_uri} ---")
        return self.ai_client.analyze_pdf_content(gcs_uri, prompt)