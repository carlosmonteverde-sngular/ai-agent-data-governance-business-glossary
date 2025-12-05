from typing import List, Dict, Any
from src.connectors.gcs_client import GCSClient
from src.connectors.dataplex_client import DataplexClient
from src.utils.config import PROJECT_ID, LOCATION, GCS_BUCKET

# Initialize clients globally or within the tools if needed. 
# For Reasoning Engine, it's often better to initialize inside the class or have them available.
# Here we will wrap them in a class or functions.

class DataplexTools:
    def __init__(self):
        self.gcs = GCSClient(PROJECT_ID)
        self.dataplex = DataplexClient(PROJECT_ID, LOCATION)

    def list_gcs_files(self, prefix: str = None) -> List[str]:
        """Lists files in the configured GCS bucket.
        
        Args:
            prefix: Optional prefix to filter files.
        """
        return self.gcs.list_files(GCS_BUCKET, prefix)

    def read_gcs_file(self, file_name: str) -> str:
        """Reads the content of a file from GCS.
        
        Args:
            file_name: The name of the file to read.
        """
        # Converting bytes to string for the LLM
        content_bytes = self.gcs.read_file(GCS_BUCKET, file_name)
        return content_bytes.decode('utf-8', errors='ignore')

    def get_dataplex_entry(self, entry_name: str) -> Dict[str, Any]:
        """Retrieves metadata for a Dataplex Entry.
        
        Args:
            entry_name: The full resource name of the entry.
        """
        # Returning dict representation of the proto
        entry = self.dataplex.get_entry(entry_name)
        return str(entry) # Return string representation for the LLM

    def update_dataplex_entry_description(self, entry_name: str, description: str):
        """Updates the description of a Dataplex Entry.
        
        Args:
            entry_name: The full resource name of the entry.
            description: The new description.
        """
        return self.dataplex.update_entry(entry_name, {'description': description}, update_mask=['description'])

    def create_data_quality_rule(self, scan_id: str, table_spec: Dict[str, Any], rule_spec: Dict[str, Any]):
        """Creates a Data Quality Rule scan.
        
        Args:
            scan_id: Unique ID for the scan.
            table_spec: Dictionary with table resource info.
            rule_spec: Dictionary defining the rule.
        """
        # This is a simplified wrapper. In reality, we might need more complex mapping.
        # For now, we assume the agent passes the correct structure or we simplify the input.
        return self.dataplex.create_quality_scan(
            parent=f"projects/{PROJECT_ID}/locations/{LOCATION}",
            scan_id=scan_id,
            table_spec=table_spec,
            rules=[rule_spec]
        )
