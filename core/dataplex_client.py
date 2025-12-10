from google.cloud import datacatalog_v1
from config.settings import config


class DataplexClient:
    """
    Client to interact with Data Catalog.
    """

    def __init__(self):
        self.client = datacatalog_v1.DataCatalogClient()

    def get_entry_context(self, linked_resource: str) -> str:
        """
        Searches for a catalog entry based on your technical resource (Lookup)
        and returns a context formatted for AI.

        Args:
            linked_resource: Full name of the resource.
                             Ej: //dataplex.googleapis.com/projects/...
                             Ej: //bigquery.googleapis.com/projects/...
        """
        try:
            # 1. Lookup:
            request = datacatalog_v1.LookupEntryRequest(linked_resource=linked_resource, location=config.LOCATION, project=config.PROJECT_ID)
            entry = self.client.lookup_entry(request=request)

            # 2. Build useful information for the agent
            # TODO: Revisar información a incluir/descartar
            info = [
                f"--- CATALOG ENTRY CONTEXT ---",
                f"Entry Name (Logic): {entry.display_name}",
                f"Type: {entry.type_.name}",
                f"Business Description: {entry.description or 'MISSING DESCRIPTION'}",
                f"Created At: {entry.source_system_timestamps.create_time}",
            ]

            # 3. Schema
            if entry.schema.columns:
                info.append("Schema Fields:")
                for col in entry.schema.columns:
                    desc = col.description if col.description else "No description"
                    info.append(f" - Field: {col.column} (Type: {col.type}) | Desc: {desc}")

            return "\n".join(info)

        except Exception as e:
            print(f"Error searching in Data Catalog: {e}")
            return "No existing catalog metadata found."