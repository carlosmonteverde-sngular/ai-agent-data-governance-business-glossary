from typing import Optional
from vertexai.generative_models import GenerativeModel

class BusinessGlossaryGenerator:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """
        Generador de Glosario de Negocio estructurado para Dataplex
        soportando Categorías y Etiquetas.
        """
        self.model = GenerativeModel(model_name)

    def _build_prompt(self, technical_context: str) -> str:
        return f"""
        Eres un experto en Gobierno de Datos y Analítica Avanzada.
        Actúa como un 'Data Steward' corporativo encargado de definir un Glosario de Negocio en Dataplex.

        TU TAREA:
        Analiza los siguientes METADATOS TÉCNICOS de BigQuery y estructura un Glosario de Negocio lógico.
        
        CONTEXTO TÉCNICO (Tablas y Columnas):
        -------------------------------------
        {technical_context}
        -------------------------------------

        REQUISITOS DE ESTRUCTURA (DATAPLEX STYLE):
        1. **Categorías**: Agrupa los términos en categorías funcionales (ej. 'Health', 'Finance', 'Customer').
           - Cada categoría debe tener: 'display_name', 'description' (corta), 'overview' (explicación detallada), y 'labels'.
        2. **Términos**: Dentro de cada categoría, lista los términos de negocio.
           - Cada término debe tener: 'term', 'definition' (funcional, NO técnica), y sugerencia de 'stewards' (roles).

        SALIDA ESPERADA (JSON ÚNICAMENTE):
        {{
          "glossary": {{
            "categories": [
              {{
                "id": "health_category",
                "display_name": "Health",
                "description": "Core health-related concepts and terminology.",
                "overview": "This category groups core health-related concepts used to describe, identify, and classify diseases...",
                "labels": {{
                  "domain": "clinical",
                  "subdomain": "health"
                }},
                "terms": [
                  {{
                    "term": "Disease Name",
                    "definition": "Official and commonly used medical name for a specific condition.",
                    "related_technical_column": "Enfermedad"
                  }}
                ]
              }}
            ]
          }}
        }}

        REGLAS:
        - Infiere las categorías basándote en el contenido de las tablas.
        - Inventa descripciones ricas y profesionales ('overview').
        - Usa etiquetas ('labels') útiles como 'domain', 'data_sensitivity', 'source_system'.
        - Responde SOLO EL JSON VÁLIDO.
        """

    def suggest_glossary_structure(self, technical_context: str) -> Optional[str]:
        """
        Genera la estructura del glosario basada en el contexto técnico proporcionado.
        """
        prompt = self._build_prompt(technical_context)
        print("🧠 Gemini analizando estructura de glosario (Categorías + Etiquetas)...")
        
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                return response.text.replace("```json", "").replace("```", "").strip()
        except Exception as e:
            print(f"❌ Error generando glosario: {e}")
        
        return None
