import os
from google.cloud import bigquery

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

def main(project_id=PROJECT_ID, location=LOCATION, target_dataset=TARGET_DATASET, glossary_id="business-glossary-v1", glossary_display_name="Business Glossary", data_source="bigquery", drive_folder_id=""):
    print("🚀 Lanzando Agente de Glosario (Vertex AI + Contexto Dinámico)")

    # Inicialización
    # vertexai.init no longer needed for google-genai client logic inside classes
    github_client = GitHubClient()

    # PASO 1: Búsqueda de contexto
    if data_source == "google_drive" and drive_folder_id:
        print(f"🔍 Recuperando PDFs desde Google Drive (Carpeta ID: '{drive_folder_id}')...")
        from modules.drive_pdf_reader import DrivePDFReader
        reader = DrivePDFReader()
        contexto_metadatos = reader.get_context_from_drive_folder(drive_folder_id)
    else:
        print(f"🔍 Recuperando metadatos de BigQuery para dataset '{target_dataset}'...")
        contexto_metadatos = get_context_from_bigquery(project_id, location, target_dataset)

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

        # --- STEP 3: CREATE PULL REQUEST ---
        print("\n🚀 Generando Pull Request con la propuesta...")
        try:
            if github_client.repo:
                pr_url = github_client.create_proposal_pr(clean_json, "business_glossary")
                print(f"✅ Pull Request creado exitosamente: {pr_url}")
                # print("💡 Esperando aprobación (Review) en GitHub para proceder mediante Github Actions.")
            else:
                print("⚠️ No hay repositorio GitHub configurado o el token falló. Solo se guardó local.")
        except Exception as e:
            print(f"❌ Error al crear el Pull Request en GitHub: {e}")

        # --- STEP 4: PUBLISH TO DATAPLEX ---
        print("\n💡 La publicación automática a Dataplex desde el script principal ha sido desactivada.")
        print("💡 Para publicar el Glosario, por favor aprueba y haz 'Merge' del Pull Request generado en GitHub.")
        print("💡 El proceso de GitHub Actions se encargará de esto automáticamente.")
        
        # try:
        #     # 1. Init Client
        #     from modules.dataplex_client import DataplexGlossaryClient
        #     import json
        #     import unicodedata
        #     import re
        #     
        #     dp_client = DataplexGlossaryClient(project_id, location)
        #     
        #     # 2. Parse JSON
        #     glossary_data = json.loads(clean_json) # clean_json is a string
        #     root = glossary_data.get("glossary", {})
        #     categories = root.get("categories", [])
        #     
        #     # 2.5 Delete existing glossary (if any) to start fresh
        #     print(f"🧹 Borrando glosario existente para carga desde cero: {glossary_id}...")
        #     dp_client.delete_glossary(glossary_id)
        #     
        #     # 3. Create Root Glossary
        #     dp_client.create_or_update_glossary(glossary_id, glossary_display_name, "Corporate Glossary generated by AI Agent")
        #     
        #     # 4. Iterate Categories
        #     term_count = 0
        #     for cat in categories:
        #         # Sanitize ID
        #         cat_original_id = cat.get("id")
        #         # Simple sanitation (can be improved)
        #         safe_cat_id = re.sub(r'[^a-zA-Z0-9-]', '', cat_original_id.lower().replace("_", "-").replace(" ", "-"))
        #         
        #         dp_client.create_category(
        #             glossary_id,
        #             safe_cat_id,
        #             cat.get("display_name", cat_original_id),
        #             cat.get("description", ""),
        #             labels=cat.get("labels")
        #         )
        #         
        #         # 5. Create Terms inside this Category
        #         cat_terms = cat.get("terms", [])
        #         for term in cat_terms:
        #             term_name = term.get("term", "Unnamed")
        #             safe_term_id = re.sub(r'[^a-zA-Z0-9-]', '', term_name.lower().replace("_", "-").replace(" ", "-"))[:60]
        #             
        #             dp_client.create_term(
        #                 glossary_id,
        #                 safe_term_id,
        #                 term_name,
        #                 term.get("definition", ""),
        #                 parent_category_id=safe_cat_id,
        #                 labels=term.get("labels")
        #             )
        #             term_count += 1
        #     
        #     print("✅ Publicación en Dataplex completada.")
        #     
        #     # --- STEP 5: AUDIT LOG ---
        #     try:
        #         print("📝 Registrando evento de publicación en Audit Log de BigQuery...")
        #         from modules.audit_logger import AuditLogger
        #         audit = AuditLogger(project_id, "openFormatHealthcare")
        #         audit.log_event(
        #             status="APPROVED_AND_PUBLISHED", 
        #             actor=os.getenv("GITHUB_ACTOR", "ai_agent"), 
        #             glossary_id=glossary_id, 
        #             details={"file": local_filename, "terms_count": term_count}
        #         )
        #         print("✅ Evento registrado en BigQuery exitosamente.")
        #     except Exception as audit_e:
        #         print(f"⚠️ No se pudo registrar en Audit Log: {audit_e}")
        #
        # except Exception as e:
        #     print(f"❌ Error publicando en Dataplex: {e}")
        #     try:
        #         from modules.audit_logger import AuditLogger
        #         audit = AuditLogger(project_id, "openFormatHealthcare")
        #         audit.log_event(
        #             status="FAILED", 
        #             actor=os.getenv("GITHUB_ACTOR", "ai_agent"), 
        #             glossary_id=glossary_id, 
        #             details={"error": str(e)}
        #         )
        #     except:
        #         pass

if __name__ == "__main__":
    main()