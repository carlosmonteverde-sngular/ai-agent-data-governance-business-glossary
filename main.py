from config.settings import config
from core.vertex_client import VertexAIClient
from core.dataplex_client import DataplexClient
from modules.metadata import MetadataEnricher


def main():
    """
    Principal orchestrator of the Agent of Government.
    """
    print("Launching Data Governance Agent")

    # 1. Initialize Clients
    try:
        vertex_client = VertexAIClient()
        dataplex_client = DataplexClient()
    except Exception as e:
        print(f"Error initializing clients: {e}")
        return


    # We build the native Resource Name of BigQuery.
    # Data Catalog will resolve this to the correct Entry, whether it has Dataplex above.
    resource_name = (
        f"//bigquery.googleapis.com/projects/{config.PROJECT_ID}"
        f"/datasets/{config.DATASET_ID}/tables/{config.TABLE_ID}"
    )

    # PDF file of documentation (in GCS)
    demo_file_name = "Presentacion_Medicina_Terminologia.pdf"  # O el fichero que subiste
    gcs_uri = f"gs://{config.GCS_BUCKET}/{demo_file_name}"

    # Instantiate use cases
    # 1.- Metadata
    metadata_module = MetadataEnricher(vertex_client)
    # 2.- Catalog
    # 3.- Quality

    # --- STEP 1: Get Current Context from the Catalog ---
    print(f"\nQuerying Data Catalog...")
    print(f"   Resource: {resource_name}")

    # Getting context from BigQuery reference
    current_context = dataplex_client.get_entry_context(resource_name)

    print(f"\nRecovered context:\n{current_context}\n")

    # --- STEP 2: Generation of Metadata with VertexAI ---
    print("Analyzing Documentation (PDF) vs Current Context...")
    metadata_result = metadata_module.suggest_metadata(gcs_uri, current_context)

    if metadata_result:
        print("\nGOVERNMENT SUGGESTIONS (JSON):")
        print(metadata_result)
    else:
        print("\nNo suggestions could be generated.")

    # --- STEP 3: CATALOG ---

    # --- STEP 3: QUALITY ---
    print("\nFinished Data Governance Agent")


if __name__ == "__main__":
    main()