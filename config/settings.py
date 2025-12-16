import os
from dataclasses import dataclass
from dotenv import load_dotenv
from google.cloud import secretmanager
import google.auth


@dataclass
class Config:
    """
    Centralized configuration class for the application.
    It loads environment variables and sets defaults.
    """
    # Load Global Vars
    load_dotenv(f"{os.getcwd()}/config/.env")

    # --- GCP Config ---
    PROJECT_ID: str = os.getenv("PROJECT_ID")
    LOCATION: str = os.getenv("LOCATION")
    GCS_BUCKET: str = os.getenv("GCS_BUCKET")
    DATASET_ID: str = os.getenv("DATASET_ID")
    TABLE_ID: str = os.getenv("TABLE_ID")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    # TODO revisar modelo más adecuado
    MODEL_NAME: str = "gemini-2.5-flash-lite"

    # --- GitHub Config ---
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")  # Ej: "usuario/repo"
    GITHUB_BASE_BRANCH: str = os.getenv("GITHUB_BASE_BRANCH", "main")
    GITHUB_SECRET_NAME: str = os.getenv("GITHUB_SECRET_NAME", "github-token-agent")
    # --- Flask Config ---
    PORT: int = os.environ.get("PORT", 8080)

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


    @property
    def GITHUB_TOKEN(self) -> str:
        return self._fetch_secret(self.GITHUB_SECRET_NAME)


    def _fetch_secret(self, secret_id: str, version_id: str = "latest") -> str:
        try:
            # Crea el cliente de Secret Manager
            client = secretmanager.SecretManagerServiceClient()

            # Construye el nombre del recurso
            name = f"projects/{self.PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"

            # Accede al secreto
            response = client.access_secret_version(request={"name": name})

            # Decodifica el payload (bytes -> string)
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Error recuperando secreto {secret_id}: {e}")
            return ""

config = Config()