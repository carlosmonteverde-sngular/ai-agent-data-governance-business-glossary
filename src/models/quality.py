from pydantic import BaseModel, Field
from typing import Optional

class QualityRule(BaseModel):
    column: str = Field(..., description="The column this rule applies to.")
    dimension: str = Field(..., description="Data quality dimension (e.g., COMPLETENESS, VALIDITY).")
    name: Optional[str] = Field(None, description="Human-readable name for the rule.")
    threshold: float = Field(1.0, description="Passing threshold (0.0 to 1.0).")
    sql_expression: Optional[str] = Field(None, description="Custom SQL for validity checks.")
