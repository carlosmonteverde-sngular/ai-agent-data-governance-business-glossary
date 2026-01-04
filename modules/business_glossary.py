from typing import Optional

from core.vertex_client import VertexAIClient

from google import genai
from google.genai import types


class BusinessGlossaryGenerator:
    def __init__(
        self,
        vertex_client: VertexAIClient,
        gemini_client: genai.Client,
        file_search_store_name: str,
    ):
        """
        Generador de Glosario de Negocio usando:
        - Gemini + File Search como fuente documental.
        """
        self.vertex_client = vertex_client
        self.gemini_client = gemini_client
        self.file_search_store_name = file_search_store_name

    def _build_prompt(self, context_description: str = "") -> str:
        """
        Construye el prompt para identificación de términos de negocio.
        """
        return f"""
        TU ROL: Actúa como un Data Steward experto en Gobierno del Dato.

        FUENTES DE INFORMACIÓN:
        1. El corpus documental accesible mediante File Search
           (documentación de negocio, políticas, reportes, etc.).
        2. Contexto adicional (opcional): {context_description}

        TU OBJETIVO:
        Analiza la documentación disponible e IDENTIFICA términos de negocio relevantes para crear o enriquecer un Glosario de Negocio en Dataplex.
        Un término de negocio debe ser un concepto importante para la organización.

        Devuelve un JSON con EXACTAMENTE esta estructura:

        {{
          "glossary_terms": [
            {{
              "term": "<Nombre del término>",
              "definition": "<Definición clara y concisa del término basada en los documentos>",
              "synonyms": ["<sinónimo1>", "<sinónimo2>"],
              "stewards": ["<nombre o rol del responsable si aparece en docs>"],
              "data_sensitivity_level": "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED",
              "domain": "<Área de negocio a la que pertenece>"
            }},
            // ... más términos identificados
          ]
        }}

        INSTRUCCIONES IMPORTANTES:
        - Extrae SOLO términos con definiciones claras en la documentación.
        - "data_sensitivity_level": Infiérelo del contexto.
        - Responde ÚNICAMENTE con el bloque JSON, sin explicaciones adicionales.
        """

    def suggest_glossary_terms(
        self,
        context_description: str = "Analiza todos los documentos disponibles.",
        model: str = "gemini-2.5-flash",
    ) -> Optional[str]:
        """
        Usa Gemini + File Search para sugerir términos para el Glosario de Negocio.

        :param context_description: Descripción o foco del análisis.
        :param model: Nombre del modelo de Gemini a usar.
        :return: String con el JSON devuelto por el modelo, o None si falla.
        """
        prompt = self._build_prompt(context_description)

        print("--- Initiating Business Glossary Extraction (File Search) ---")
        print(f"   Using File Search Store: {self.file_search_store_name}")
        print(f"   Model: {model}")

        try:
            response = self.gemini_client.models.generate_content(
                model=model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=prompt)],
                    )
                ],
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            file_search=types.FileSearch(
                                file_search_store_names=[self.file_search_store_name]
                            )
                        )
                    ]
                ),
            )

            result_text = getattr(response, "text", None)

            if not result_text:
                print("⚠️ No se recibió texto en la respuesta de Gemini.")
                return None

            return result_text.strip()

        except Exception as e:
            print(f"❌ Error calling Gemini with File Search: {e}")
            return None
