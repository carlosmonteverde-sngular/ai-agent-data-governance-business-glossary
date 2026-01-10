from google.cloud import bigquery
from datetime import datetime
import json

class AuditLogger:
    def __init__(self, project_id: str, dataset_id: str, table_id: str = "glossary_audit_log"):
        self.client = bigquery.Client(project=project_id)
        self.table_ref = f"{project_id}.{dataset_id}.{table_id}"
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        schema = [
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("actor", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("glossary_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("details", "STRING", mode="NULLABLE"), # JSON string
        ]
        try:
            self.client.get_table(self.table_ref)
        except Exception:
            print(f"Creating audit table {self.table_ref}...")
            table = bigquery.Table(self.table_ref, schema=schema)
            self.client.create_table(table)

    def log_event(self, status: str, actor: str = "system", glossary_id: str = None, details: dict = None):
        rows_to_insert = [
            {
                "timestamp": datetime.now().isoformat(),
                "actor": actor,
                "status": status,
                "glossary_id": glossary_id,
                "details": json.dumps(details) if details else None
            }
        ]
        errors = self.client.insert_rows_json(self.table_ref, rows_to_insert)
        if errors:
            print(f"❌ Error logging to BigQuery: {errors}")
        else:
            print(f"✅ Event logged to BigQuery: {status}")
