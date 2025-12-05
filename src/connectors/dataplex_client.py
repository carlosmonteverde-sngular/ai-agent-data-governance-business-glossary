from google.cloud import dataplex_v1
from typing import Dict, Any

class DataplexClient:
    def __init__(self, project_id: str, location: str):
        self.project_id = project_id
        self.location = location
        self.catalog_client = dataplex_v1.CatalogServiceClient()
        self.data_scan_client = dataplex_v1.DataScanServiceClient()

    def get_entry(self, entry_name: str) -> Dict[str, Any]:
        """Retrieves a Dataplex Entry.
        
        Args:
            entry_name: The full resource name of the entry.
                        projects/{project}/locations/{location}/entryGroups/{entry_group}/entries/{entry}
        """
        request = dataplex_v1.GetEntryRequest(name=entry_name)
        response = self.catalog_client.get_entry(request=request)
        return response

    def update_entry(self, entry_name: str, metadata: Dict[str, Any], update_mask: list = None):
        """Updates a Dataplex Entry with new metadata.
        
        Args:
            entry_name: The full resource name of the entry.
            metadata: Dictionary containing the fields to update (e.g., description, user_defined_system).
            update_mask: List of fields to update.
        """
        entry = self.get_entry(entry_name)
        
        # Update fields based on metadata dict
        if 'description' in metadata:
            entry.description = metadata['description']
        if 'display_name' in metadata:
            entry.display_name = metadata['display_name']
            
        # Update mask construction
        from google.protobuf import field_mask_pb2
        mask = field_mask_pb2.FieldMask(paths=update_mask if update_mask else ['description', 'display_name'])
        
        request = dataplex_v1.UpdateEntryRequest(
            entry=entry,
            update_mask=mask
        )
        return self.catalog_client.update_entry(request=request)

    def create_quality_scan(self, parent: str, scan_id: str, table_spec: Dict[str, Any], rules: List[Dict[str, Any]]):
        """Creates a Data Quality Scan.
        
        Args:
            parent: projects/{project}/locations/{location}
            scan_id: Unique ID for the scan.
            table_spec: Dict with 'full_table_name' (BigQuery) or 'resource_path' (GCS).
            rules: List of DataQualityRule dictionaries.
        """
        data_quality_spec = dataplex_v1.DataQualitySpec(rules=rules)
        
        data_scan = dataplex_v1.DataScan(
            data_quality_spec=data_quality_spec,
            data=dataplex_v1.DataSource(
                resource=table_spec.get('resource_path'),
                entity=table_spec.get('entity') 
            )
        )
        
        request = dataplex_v1.CreateDataScanRequest(
            parent=parent,
            data_scan_id=scan_id,
            data_scan=data_scan
        )
        
        return self.data_scan_client.create_data_scan(request=request)
