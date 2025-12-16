from github import Github
from config.settings import config
import time


class GitHubClient:
    def __init__(self):
        if not config.GITHUB_TOKEN:
            print("GITHUB_TOKEN not found.")
            self.repo = None
            return

        self.github = Github(config.GITHUB_TOKEN)
        self.repo = self.github.get_repo(config.GITHUB_REPO)

    def create_proposal_pr(self, file_content: str, entity_name: str) -> str:
        if not self.repo:
            raise ValueError("GitHub Repo not initialized (Check Token).")

        timestamp = int(time.time())
        branch_name = f"governance/suggestion-{entity_name}-{timestamp}"
        file_path = f"output/{entity_name}_metadata_v{timestamp}.json"

        # 1. Referencia a main
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