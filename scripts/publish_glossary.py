import sys
import os

# Add the project root directory to sys.path so we can import 'modules'
# This assumes the script is located at [project_root]/scripts/publish_glossary.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import uuid
import unicodedata
import re
from google.cloud import bigquery
from modules.dataplex_client import DataplexGlossaryClient
from modules.audit_logger import AuditLogger

# Configuration (Env vars or defaults)
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "pg-gccoe-carlos-monteverde")
LOCATION = os.getenv("GCP_LOCATION", "us")
DATASET_ID = "openFormatHealthcare" # For Audit Log
GLOSSARY_ID = "business-glossary-v1" # Fixed ID (hyphens only)

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
        
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
    except Exception as e:
        print(f"❌ Error reading glossary file: {e}")
        return

    # 2. Init Clients
    client = DataplexGlossaryClient(PROJECT_ID, LOCATION)
    audit = AuditLogger(PROJECT_ID, DATASET_ID)
    
    actor = os.getenv("GITHUB_ACTOR", "unknown_user")

    try:
        # 3. Clean up existing glossary to ensure fresh start
        client.delete_glossary(GLOSSARY_ID)
        
        # 4. Create Glossary
        # Expected structure from BusinessGlossaryGenerator:
        # { "glossary": { "categories": [...], "terms": [...] } }
        
        # Create root glossary container
        # Create/Update root glossary
        client.create_or_update_glossary(GLOSSARY_ID, "Business Glossary", "Corporate Business Glossary")
        
        # Parse new structure: { "glossary": { "categories": [...], "terms": [...] } }
        glossary_data = data.get("glossary", {})
        categories = glossary_data.get("categories", [])
        terms = glossary_data.get("terms", [])
        
        print(f"📊 Found {len(categories)} categories and {len(terms)} terms.")

        # 1. Create Categories
        # Map original ID from JSON to sanitized ID for Dataplex
        cat_id_map = {} 

        for cat in categories:
            original_id = cat.get("id")
            # Sanitize ID: normalize to NFKD form to split accents, encode to ascii ignoring non-ascii, decode back
            normalized = unicodedata.normalize('NFKD', original_id).encode('ascii', 'ignore').decode('utf-8')
            # Replace spaces/underscores with hyphens and keep only alphanumeric/hyphens
            safe_id = re.sub(r'[^a-zA-Z0-9-]', '', normalized.lower().replace("_", "-").replace(" ", "-"))
            # Ensure no double hyphens
            safe_id = re.sub(r'-+', '-', safe_id).strip('-')
            
        for cat in categories:
            original_id = cat.get("id")
            # Sanitize ID: normalize to NFKD form to split accents, encode to ascii ignoring non-ascii, decode back
            normalized = unicodedata.normalize('NFKD', original_id).encode('ascii', 'ignore').decode('utf-8')
            # Replace spaces/underscores with hyphens and keep only alphanumeric/hyphens
            safe_id = re.sub(r'[^a-zA-Z0-9-]', '', normalized.lower().replace("_", "-").replace(" ", "-"))
            # Ensure no double hyphens
            safe_id = re.sub(r'-+', '-', safe_id).strip('-')
            
            cat_id_map[original_id] = safe_id
            
            # User requested Overview to be separate, but API doesn't support it in v1.
            # We will NOT append it to description as requested ("manual").
            cat_desc = cat.get("description", "")
            
            client.create_category(
                GLOSSARY_ID, 
                safe_id, 
                cat.get("display_name", original_id), 
                cat_desc,
                labels=cat.get("labels", {})
            )

        # 2. Create Terms
        term_count = 0
        for term in terms:
            term_name = term.get("term", "Unnamed")
            
            # User requested to keep Description clean (only definition).
            # Overview, Related Terms, Synonyms, Contacts will be filled manually.
            rich_description = term.get("definition", "No definition provided.")
            
            # Sanitize Term ID
            normalized_term = unicodedata.normalize('NFKD', term_name).encode('ascii', 'ignore').decode('utf-8')
            term_id = re.sub(r'[^a-zA-Z0-9-]', '', normalized_term.lower().replace(" ", "-").replace("/", "-").replace("_", "-"))
            term_id = re.sub(r'-+', '-', term_id).strip('-')[:99]
            
            # Find parent category ID
            parent_cat_name = term.get("parent_category")
            parent_cat_id = None
            
            # We need to map 'parent_category' Name -> Category ID
            # Let's rebuild a map from category display_name -> original_id -> safe_id
            cat_name_to_id = {c.get("display_name"): cat_id_map.get(c.get("id")) for c in categories}
            
            if parent_cat_name:
                parent_cat_id = cat_name_to_id.get(parent_cat_name)
                # Fallback: if name matches ID directly (check original IDs)
                if not parent_cat_id:
                     # Check if 'parent_category' matches one of the original IDs
                     if parent_cat_name in cat_id_map:
                         parent_cat_id = cat_id_map[parent_cat_name]

            # Add Technical Column to labels if possible (sanitized)
            term_labels = term.get("labels", {})
            if term.get("related_technical_column"):
                # Labels keys must be lowercase, numbers, underscores, hyphens. Max 63 chars.
                # We will use a generic key 'related_technical_column' and truncate the value if needed?
                # Wait, label values also have restrictions.
                # Let's try to put it in labels.
                tech_col = term.get("related_technical_column")
                # Sanitize value for label (lowercase, etc? No, values can contain unicode but usually restricted)
                # Dataplex Label values: max 63 chars, lowercase, digits, -_
                # Columns like 'pharmaceutical_drugs.drug_molecule.id' are too long/complex for label values usually.
                # We will skip adding it to labels to avoid errors, as user said "Related entries" (which we can't do easily).
                pass

            client.create_term(
                GLOSSARY_ID, 
                term_id, 
                term_name, 
                rich_description, 
                parent_category_id=parent_cat_id,
                labels=term_labels
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
