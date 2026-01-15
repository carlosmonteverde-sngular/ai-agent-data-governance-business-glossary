import os
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel
from core.github_client import GitHubClient

# --- CONFIGURACIÓN TÉCNICA ---
PROJECT_ID = "pg-gccoe-carlos-monteverde" 
LOCATION = "us" 
TARGET_DATASET = "pharmaceutical_drugs"
# DATA_STORE_ID ya no es necesario para este enfoque

def get_context_from_bigquery(project_id: str, location: str, dataset_id: str) -> str:
    """
    Recupera el contexto de los metadatos de las tablas en BigQuery de un dataset específico.
    """
    client = bigquery.Client(project=project_id, location=location)
    context = ""
    
    try:
        print(f"DEBUG: Listando tablas en el dataset '{dataset_id}'...")
        # Construir referencia completa del dataset
        dataset_ref = f"{project_id}.{dataset_id}"
        
        try:
            # Verificar si existe el dataset y listar tablas directo
            tables = list(client.list_tables(dataset_id))
        except Exception as e:
            print(f"⚠️ Error accediendo al dataset {dataset_id}: {e}")
            return ""

        if not tables:
             print(f"⚠️ No se encontraron tablas en {dataset_id}.")
             return ""

        context += f"\nDataset: {dataset_id}\n"
        
        for table in tables:
            # Obtener detalles completos de la tabla para ver descripción y esquema
            full_table = client.get_table(table)
            
            context += f"  Table: {full_table.table_id}\n"
            if full_table.description:
                context += f"    Description: {full_table.description}\n"
            
            context += "    Columns:\n"
            for schema_field in full_table.schema:
                desc_str = f" - Description: {schema_field.description}" if schema_field.description else ""
                context += f"      - {schema_field.name} ({schema_field.field_type}){desc_str}\n"

    except Exception as e:
        print(f"⚠️ Error recuperando metadatos de BigQuery: {e}")
        return ""

    return context.strip()

def main():
    print("🚀 Lanzando Agente de Glosario (Vertex AI + BigQuery Metadata)")

    # Inicialización
    vertexai.init(project=PROJECT_ID, location="us-central1")
    model = GenerativeModel("gemini-2.5-flash")
    github_client = GitHubClient()

    # PASO 1: Búsqueda de contexto en BigQuery
    print(f"🔍 Recuperando metadatos de BigQuery para dataset '{TARGET_DATASET}'...")
    contexto_metadatos = get_context_from_bigquery(PROJECT_ID, LOCATION, TARGET_DATASET)

    if not contexto_metadatos:
        print("❌ No se pudo recuperar ningún contexto de metadatos de BigQuery.")
        print("💡 Verifica permisos o que existan datasets/tablas en la ubicación configurada.")
        return

    print(f"✅ Contexto recuperado ({len(contexto_metadatos)} caracteres).")

    # PASO 2: Generar glosario Estructurado
    from modules.business_glossary import BusinessGlossaryGenerator
    
    glossary_gen = BusinessGlossaryGenerator(model_name="gemini-2.5-flash")
    clean_json = glossary_gen.suggest_glossary_structure(contexto_metadatos)
    
    if clean_json:
        print("\nSugerencia generada (Estructura Dataplex):")
        print(clean_json)

        # --- STEP 2.1: Save to Local Output (for manual publishing/debug) ---
        import time
        
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(time.time())
        local_filename = f"{output_dir}/glossary_proposal_{timestamp}.json"
        
        with open(local_filename, "w", encoding="utf-8") as f:
            f.write(clean_json)
        
        print(f"\n✅ Propuesta guardada localmente en: {local_filename}")

        # --- STEP 3: GITHUB PR ---
        # We can use a custom branch or file name for glossary
        try:
            pr_url = github_client.create_proposal_pr(clean_json, "business_glossary_update")
            print(f"\n✅ Proceso completado. PR: {pr_url}")
        except Exception as e:
            print(f"❌ Error GitHub: {e}")

if __name__ == "__main__":
    main()