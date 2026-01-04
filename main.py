import os
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1beta as discoveryengine
import vertexai
from vertexai.generative_models import GenerativeModel
from core.github_client import GitHubClient

# --- CONFIGURACIÓN TÉCNICA ---
PROJECT_ID = "pg-gccoe-carlos-monteverde" 
LOCATION = "us" 
DATA_STORE_ID = "data-governance-ai-agent_1767099540851" 

def get_context_from_data_store(query: str) -> str:
    """
    Recupera contexto intentando múltiples campos de datos para Standard Edition.
    """
    client_options = ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
    client = discoveryengine.SearchServiceClient(client_options=client_options)
    
    # Path del motor de búsqueda
    serving_config = f"projects/{PROJECT_ID}/locations/{LOCATION}/dataStores/{DATA_STORE_ID}/servingConfigs/default_config"

    # Solicitud básica compatible con Standard Edition
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=5
    )

    try:
        response = client.search(request)
        context = ""
        
        found_docs = list(response.results)
        print(f"DEBUG: Documentos localizados en la búsqueda: {len(found_docs)}")
        
        for result in found_docs:
            data = result.document.derived_struct_data
            
            # Intento 1: Snippets (Fragmentos estándar)
            snippets = data.get("snippets", [])
            for s in snippets:
                text = s.get("snippet", "")
                if text:
                    context += text + "\n"
            
            # Intento 2: Extracción directa de campos de texto si existen
            # A veces en Standard, el texto se mapea a campos genéricos
            ext_data = data.get("extractive_segments", [])
            for segment in ext_data:
                content = segment.get("content", "")
                if content:
                    context += content + "\n"

        return context.strip()
    except Exception as e:
        print(f"⚠️ Error en la búsqueda: {e}")
        return ""

def main():
    print("🚀 Lanzando Agente de Glosario (Vertex AI Search - Standard Edition)")

    # Inicialización
    vertexai.init(project=PROJECT_ID, location="us-central1")
    model = GenerativeModel("gemini-1.5-flash")
    github_client = GitHubClient()

    # PASO 1: Búsqueda de contenido
    # IMPORTANTE: He cambiado la query a una sola palabra clave para maximizar resultados
    query_test = "Presentacion" 
    print(f"🔍 Consultando Data Store por: '{query_test}'...")
    contexto_docs = get_context_from_data_store(query_test)

    if not contexto_docs:
        print("❌ El motor encontró los archivos pero no pudo extraer texto legible.")
        print("💡 Acción recomendada: Ve a la consola de Google Cloud, entra en tu Data Store,")
        print("   haz clic en el PDF y verifica en 'Document JSON' si el campo 'text' tiene contenido.")
        return

    # PASO 2: Generar glosario JSON
    prompt = f"""
    Eres un experto en Gobierno de Datos. Basándote en este texto:
    
    {contexto_docs}
    
    Genera un glosario de términos de negocio en JSON:
    {{
      "glossary_terms": [
        {{ "term": "nombre", "definition": "definición" }}
      ]
    }}
    Responde solo el JSON.
    """

    print("🧠 Gemini analizando el texto...")
    response = model.generate_content(prompt)
    
    if response.text:
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        print("\nSugerencia generada:")
        print(clean_json)

        # PASO 3: GitHub
        try:
            pr_url = github_client.create_proposal_pr(clean_json, "glossary_update")
            print(f"\n✅ Proceso completado. PR: {pr_url}")
        except Exception as e:
            print(f"❌ Error GitHub: {e}")

if __name__ == "__main__":
    main()