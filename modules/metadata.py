from typing import Optional

from core.vertex_client import VertexAIClient

from google import genai
from google.genai import types


class MetadataEnricher:
    def __init__(
        self,
        vertex_client: VertexAIClient,
        gemini_client: genai.Client,
        file_search_store_name: str,
    ):
        """
        Enriquecedor de metadatos usando:
        - Vertex (para lo que ya tengas en tu cliente).
        - Gemini + File Search como fuente documental.
        """
        self.vertex_client = vertex_client
        self.gemini_client = gemini_client
        self.file_search_store_name = file_search_store_name

    def _build_prompt(self, existing_metadata_context: str) -> str:
        """
        Construye el prompt que se enviará a Gemini.
        Aquí pedimos explícitamente sugerencias a nivel de tabla y de campos.
        """
        return f"""
        TU ROL: Actúa como un Data Steward experto.

        TIENES DOS FUENTES DE INFORMACIÓN:
        1. El corpus documental accesible mediante File Search
           (documentación técnica/negocio ya indexada en el File Search Store).
        2. Los metadatos técnicos actuales extraídos de Dataplex (incluyendo ESQUEMA y CAMPOS):
           --- INICIO METADATOS ACTUALES ---
           {existing_metadata_context}
           --- FIN METADATOS ACTUALES ---

        TU OBJETIVO:
        Eres un agente de metadatos de Dataplex. Debes analizar si la definición actual
        en Dataplex (tabla y campos) coincide con la documentación del corpus.

        Devuelve un JSON con EXACTAMENTE esta estructura:

        {{
          "metadata_update": [
            {{
              "field": "Business Description",
              "description": "<nueva descripción de la tabla si procede, en el idioma del contexto>"
            }},
            {{
              "field": "Schema Fields",
              "description": [
                {{
                  "field": "<nombre de la columna 1>",
                  "description": "<descripción de negocio sugerida para la columna 1>"
                }},
                {{
                  "field": "<nombre de la columna 2>",
                  "description": "<descripción de negocio sugerida para la columna 2>"
                }}
                // Incluir TODAS las columnas del esquema actual
              ]
            }}
          ],
          "missing_fields": [
            {{
              "field": "<nombre de un campo que aparezca en la documentación pero no en el esquema actual>",
              "reason": "<por qué consideras que falta>"
            }}
          ],
          "business_domain": "<dominio de negocio inferido para la tabla>",
          "data_quality_flag": "GREEN" | "RED"
        }}

        INSTRUCCIONES IMPORTANTES:

        - En "Schema Fields" debes recorrer TODAS las columnas que aparezcan en el esquema
          actual de Dataplex (las que vienen en el contexto bajo 'Field: ...').
        - Para cada columna, propone una "description" de negocio basada en la documentación.
          Si no encuentras información suficiente, usa una descripción razonable basada en
          el nombre del campo y la descripción técnica.
        - Mantén los nombres de los campos EXACTAMENTE como aparecen en el esquema.
        - "missing_fields" solo debe usarse si la documentación menciona campos que NO están
          en el esquema actual.
        - "data_quality_flag" será GREEN si ves coherencia entre documentación y esquema,
          RED si encuentras contradicciones importantes. Si es RED, indicame las salidas que has tenido en coherencia apra entender el por qué esto
        - Responde ÚNICAMENTE con el bloque JSON, sin explicaciones adicionales.
        """

    def suggest_metadata_with_file_search(
        self,
        current_context: str,
        model: str = "gemini-2.5-flash",
    ) -> Optional[str]:
        """
        Usa Gemini + File Search para analizar el contexto actual de Dataplex
        y sugerir enriquecimiento de metadatos (tabla + campos).

        :param current_context: Contexto de metadatos de Dataplex.
        :param model: Nombre del modelo de Gemini a usar.
        :return: String con el JSON devuelto por el modelo, o None si falla.
        """
        prompt = self._build_prompt(current_context)

        print("--- Initiating cross-analysis (File Search vs Dataplex) ---")
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
