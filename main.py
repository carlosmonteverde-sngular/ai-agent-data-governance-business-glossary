from config.settings import config
from core.vertex_client import VertexAIClient
from core.dataplex_client import DataplexClient
from modules.metadata import MetadataEnricher



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
    Principal orchestrator of the Data Governance Agent.
    """
    print("Launching Data Governance Agent")

    # 1. Initialize Clients
    try:
        # Cliente para Vertex (lo que ya tuvieras montado)
        vertex_client = VertexAIClient()

        # Cliente para Dataplex
        dataplex_client = DataplexClient()

        # Cliente Gemini *Developer* (para File Search)
        gemini_client = create_gemini_client()

        # Cliente Github
        github_client = GitHubClient()

    except Exception as e:
        print(f"Error initializing clients: {e}")
        return

    # --- STEP 0: Build BigQuery resource name ---
    resource_name = (
        f"//bigquery.googleapis.com/projects/{config.PROJECT_ID}"
        f"/datasets/{config.DATASET_ID}/tables/{config.TABLE_ID}"
    )

    # --- STEP 0.1: File Search Store (creado / resuelto vía código) ---
    file_search_display_name = getattr(
        config, "FILE_SEARCH_STORE_DISPLAY_NAME", "datagov-docs-store"
    )

    file_search_store_name = get_or_create_file_search_store(
        gemini_client=gemini_client,
        display_name=file_search_display_name,
    )

    # --- (Opcional) STEP 0.2: Importar documentos al store ---
    # Esto normalmente lo harías una única vez en un script de bootstrap.
    # Te dejo el ejemplo por si quieres integrarlo aquí:
    #
    # docs_to_import = [
    #     "docs/Presentacion_Metadatos.pdf",
    #     "docs/Normativa_Datagov.pdf",
    # ]
    # for path in docs_to_import:
    #     print(f"📄 Importando documento al File Search Store: {path}")
    #     operation = gemini_client.file_search_stores.upload_to_file_search_store(
    #         file_search_store_name=file_search_store_name,
    #         file=path,
    #         config={"display_name": path},
    #     )
    #     print(f"   ➜ Subida lanzada para: {path}")

    # --- STEP 1: Get Current Context from the Catalog ---
    print(f"\nQuerying Data Catalog...")
    print(f"   Resource: {resource_name}")

    current_context = dataplex_client.get_entry_context(resource_name)

    print(f"\nRecovered context:\n{current_context}\n")

    # --- STEP 2: Generation of Metadata with Gemini + File Search ---
    print("Analyzing documentation corpus (File Search) vs current context...")

    metadata_module = MetadataEnricher(
        vertex_client=vertex_client,
        gemini_client=gemini_client,
        file_search_store_name=file_search_store_name,
    )

    metadata_result = metadata_module.suggest_metadata_with_file_search(
        current_context=current_context
    )

    if metadata_result:
        print("\nGOVERNANCE SUGGESTIONS (JSON):")
        print(metadata_result)
    else:
        print("\nNo suggestions could be generated.")

    print("\nFinished Data Governance Agent")

   # --- STEP 3: GITHUB PR ---∫
    clean_json = metadata_result.replace("```json", "").replace("```", "").strip()

    # 3. GitOps PR
    pr_url = github_client.create_proposal_pr(clean_json, config.TABLE_ID)

    print(f"\nFinished Data Governance Agent: PR para aprobar cambios: {pr_url}")


if __name__ == "__main__":
    main()
