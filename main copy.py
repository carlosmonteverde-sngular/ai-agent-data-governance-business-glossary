from config.settings import config
from core.vertex_client import VertexAIClient
from core.dataplex_client import DataplexClient
from modules.business_glossary import BusinessGlossaryGenerator  # Updated import



from google import genai
from google.genai import types

from core.github_client import GitHubClient

def create_gemini_client() -> genai.Client:
    """
    Crea un cliente Gemini en modo *Developer API* (NO Vertex AI),
    que es el único que soporta File Search a día de hoy.
    """
    return genai.Client(
        api_key=config.GEMINI_API_KEY  # API key de Google AI Studio
    )


def get_or_create_file_search_store(
    gemini_client: genai.Client, display_name: str
) -> str:
    """
    Devuelve el name completo de un File Search Store.

    - Si ya existe uno con ese display_name, lo reutiliza.
    - Si no existe, lo crea.

    Ejemplo de name devuelto:
        "fileStores/abcd1234..."  (o formato similar según la versión del SDK)
    """

    # 1. Buscar si ya existe un store con ese display_name
    try:
        stores = list(gemini_client.file_search_stores.list())
        for store in stores:
            # En las versiones actuales del SDK vienen como atributos directos
            if getattr(store, "display_name", None) == display_name:
                print(f"✅ Reutilizando File Search Store existente: {store.name}")
                
                # --- DEBUG: List files in the store ---
                try:
                    files = list(gemini_client.file_search_stores.list_files(name=store.name))
                    print(f"   📂 Archivos en el store: {len(files)}")
                    for f in files:
                        print(f"      - {f.display_name} (uri: {f.uri})")
                    
                    if len(files) == 0:
                        print("   ⚠️ EL STORE ESTÁ VACÍO. Necesitas subir documentos para que el agente funcione.")
                except Exception as list_err:
                    print(f"   ⚠️ No se pudieron listar los archivos: {list_err}")
                # --------------------------------------

                return store.name

    except Exception as e:
        print(f"Error listing File Search stores (no pasa nada grave): {e}")

    # 2. Si no existe, lo creamos
    print(f"⚙️  Creando nuevo File Search Store con display_name='{display_name}'...")
    file_search_store = gemini_client.file_search_stores.create(
        config={"display_name": display_name}
    )
    print(f"✅ File Search Store creado: {file_search_store.name}")

    return file_search_store.name


def main():
    """
    Principal orchestrator of the Business Glossary Agent.
    """
    print("Launching Business Glossary Agent")

    # 1. Initialize Clients
    try:
        # Cliente para Vertex (lo que ya tuvieras montado)
        vertex_client = VertexAIClient()

        # Cliente para Dataplex (Optional context)
        dataplex_client = DataplexClient()

        # Cliente Gemini *Developer* (para File Search)
        gemini_client = create_gemini_client()

        # Cliente Github
        github_client = GitHubClient()

    except Exception as e:
        print(f"Error initializing clients: {e}")
        return

    # --- STEP 0.1: File Search Store (creado / resuelto vía código) ---
    file_search_display_name = getattr(
        config, "FILE_SEARCH_STORE_DISPLAY_NAME", "datagov-docs-store"
    )

    file_search_store_name = get_or_create_file_search_store(
        gemini_client=gemini_client,
        display_name=file_search_display_name,
    )

    # --- STEP 1: Generation of Business Glossary ---
    print("\nAnalyzing documentation corpus (File Search) for Business Terms...")

    glossary_module = BusinessGlossaryGenerator(
        vertex_client=vertex_client,
        gemini_client=gemini_client,
        file_search_store_name=file_search_store_name,
    )

    # Suggest terms based on all available documents
    glossary_result = glossary_module.suggest_glossary_terms(
        context_description="Analiza documentación para identificar términos clave del negocio.",
    )

    if glossary_result:
        print("\nBUSINESS GLOSSARY SUGGESTIONS (JSON):")
        print(glossary_result)
        
        # --- STEP 2: GITHUB PR ---
        clean_json = glossary_result.replace("```json", "").replace("```", "").strip()

        # 3. GitOps PR
        # We can use a custom branch or file name for glossary
        pr_url = github_client.create_proposal_pr(clean_json, "business_glossary_update")

        print(f"\nFinished Business Glossary Agent: PR para aprobar cambios: {pr_url}")

    else:
        print("\nNo suggestions could be generated.")

    print("\nFinished Business Glossary Agent")


if __name__ == "__main__":
    main()
