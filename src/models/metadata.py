from pydantic import BaseModel, Field
from typing import List, Optional

class MetadataSuggestion(BaseModel):
    description: Optional[str] = Field(None, description="Suggested description for the data asset.")
    display_name: Optional[str] = Field(None, description="Suggested display name.")
    tags: List[str] = Field(default_factory=list, description="List of tags to apply.")
    columns: Optional[dict] = Field(None, description="Column-level metadata suggestions.")
