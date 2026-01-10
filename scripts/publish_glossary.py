import os
import json
import uuid
from google.cloud import bigquery
from modules.dataplex_client import DataplexGlossaryClient
from modules.audit_logger import AuditLogger

# Configuration (Env vars or defaults)
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "pg-gccoe-carlos-monteverde")
LOCATION = os.getenv("GCP_LOCATION", "us")
DATASET_ID = "openFormatHealthcare" # For Audit Log
GLOSSARY_ID = "business_glossary_v1" # Fixed ID for simplicity, or dynamic

def main():
    print("🚀 Starting Glossary Publishing Process...")
    
    # 1. Load JSON file
    # We assume the PR merged a file into a known path or we scan for it.
    # For this implementation, let's assume 'glossary_proposal.json' exists in root or output.
    # IN REALITY: The main.py generated a timestamped file. 
    # The CI script needs to find the *latest* file or specific file.
    # Let's verify `output/` directory for the latest JSON.
    output_dir = "output"
    try:
        files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".json")]
        if not files:
            print("❌ No glossary JSON files found in output/")
            return
        
        # Pick latest file
        latest_file = max(files, key=os.path.getmtime)
        print(f"📖 Processing file: {latest_file}")
        
        with open(latest_file, "r") as f:
            data = json.load(f)
            
    except Exception as e:
        print(f"❌ Error reading glossary file: {e}")
        return

    # 2. Init Clients
    client = DataplexGlossaryClient(PROJECT_ID, LOCATION)
    audit = AuditLogger(PROJECT_ID, DATASET_ID)
    
    actor = os.getenv("GITHUB_ACTOR", "unknown_user")

    try:
        # 3. Create/Update Glossary
        # 'data' structure expected: {"glossary": {"categories": [...]}}
        glossary_data = data.get("glossary", {})
        
        # Create root glossary container
        client.create_or_update_glossary(GLOSSARY_ID, "Business Glossary", "Corporate Business Glossary")
        
        categories = glossary_data.get("categories", [])
        term_count = 0
        
        for cat in categories:
            cat_id = cat.get("id", str(uuid.uuid4())[:8])
            cat_dn = cat.get("display_name", "Unknown Category")
            cat_desc = cat.get("overview", "") or cat.get("description", "")
            
            # Create Category (as a high-level term)
            client.create_category(GLOSSARY_ID, cat_id, cat_dn, cat_desc)
            
            # Create Terms in Category
            terms = cat.get("terms", [])
            for term in terms:
                term_name = term.get("term", "Unnamed")
                term_def = term.get("definition", "")
                term_id = term_name.lower().replace(" ", "_")[:50] # Simple slugify
                
                client.create_term(
                    GLOSSARY_ID, 
                    term_id, 
                    term_name, 
                    term_def, 
                    parent_category_id=cat_id
                )
                term_count += 1

        print(f"✅ Glossary published successfully. {len(categories)} categories, {term_count} terms.")
        
        # 4. Audit Log
        audit.log_event(
            status="APPROVED_AND_PUBLISHED", 
            actor=actor, 
            glossary_id=GLOSSARY_ID, 
            details={"file": latest_file, "terms_count": term_count}
        )

    except Exception as e:
        print(f"❌ Error publishing glossary: {e}")
        audit.log_event(
            status="FAILED", 
            actor=actor, 
            glossary_id=GLOSSARY_ID, 
            details={"error": str(e)}
        )
        raise e

if __name__ == "__main__":
    main()
