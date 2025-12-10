import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Config:
    """
    Centralized configuration class for the application.
    It loads environment variables and sets defaults.
    """

    load_dotenv(f"{os.getcwd()}/config/.env")

    PROJECT_ID: str = os.getenv("PROJECT_ID")
    LOCATION: str = os.getenv("LOCATION")
    GCS_BUCKET: str = os.getenv("GCS_BUCKET")
    DATASET_ID: str = os.getenv("DATASET_ID")
    TABLE_ID: str = os.getenv("TABLE_ID")
    # TODO revisar modelo más adecuado
    MODEL_NAME: str = "gemini-2.5-flash-lite"

    def __post_init__(self):
        # Validation of global variables
        missing_fields = [
            field_name for field_name, value in vars(self).items()
            if value is None
        ]

        if missing_fields:
            raise ValueError(
                "Initialization Error: The following fields cannot be None: "
                f"{', '.join(missing_fields)}"
            )

config = Config()