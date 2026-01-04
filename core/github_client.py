from github import Github
from config.settings import config
import time

class GitHubClient:
    def __init__(self):
        # Retrieve the actual token using the property that calls Secret Manager
        token = config.GITHUB_TOKEN

        if not token:
            print("GITHUB_TOKEN could not be retrieved (Check Secret Manager access).")
            self.repo = None
            return

        # Initialize with the retrieved token
        self.github = Github(token)
        
        try:
            self.repo = self.github.get_repo(config.GITHUB_REPO)
        except Exception as e:
            print(f"Error accessing repo: {e}")
            self.repo = None

    def create_proposal_pr(self, file_content: str, entity_name: str) -> str:
        if not self.repo:
            raise ValueError("GitHub Repo not initialized (Check Secret/Token).")

        timestamp = int(time.time())
        branch_name = f"governance/suggestion-{entity_name}-{timestamp}"
        file_path = f"output/{entity_name}_metadata_v{timestamp}.json"

        # 1. Referencia a la rama base
        base_ref = self.repo.get_git_ref(f"heads/{config.GITHUB_BASE_BRANCH}")

        # 2. Crear rama
        self.repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)

        # 3. Subir fichero JSON
        self.repo.create_file(
            path=file_path,
            message=f"chore: Update metadata for {entity_name}",
            content=file_content,
            branch=branch_name
        )

        # 4. Crear Pull Request
        pr = self.repo.create_pull(
            title=f"[Agent] Metadata Proposal: {entity_name}",
            body=f"Sugerencia automática de gobierno para `{entity_name}` basada en documentación.",
            head=branch_name,
            base=config.GITHUB_BASE_BRANCH
        )

        return pr.html_url