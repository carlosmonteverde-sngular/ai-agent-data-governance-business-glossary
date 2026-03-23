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

        branch_name = f"governance/suggestion-{entity_name}"
        file_path = f"output/{entity_name}_metadata.json"

        # 1. Comprobar si la rama ya existe
        branch_exists = False
        try:
            self.repo.get_branch(branch_name)
            branch_exists = True
        except Exception:
            branch_exists = False

        if not branch_exists:
            # 1b. Referencia a la rama base
            base_ref = self.repo.get_git_ref(f"heads/{config.GITHUB_BASE_BRANCH}")
            # 2. Crear rama
            self.repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_ref.object.sha)

        # 3. Subir o actualizar fichero JSON
        try:
            # Intentar obtener el archivo si existe para actualizarlo
            contents = self.repo.get_contents(file_path, ref=branch_name)
            self.repo.update_file(
                path=file_path,
                message=f"chore: Update metadata for {entity_name}",
                content=file_content,
                sha=contents.sha,
                branch=branch_name
            )
        except Exception:
            # El archivo no existe en esta rama, crearlo
            self.repo.create_file(
                path=file_path,
                message=f"chore: Create metadata for {entity_name}",
                content=file_content,
                branch=branch_name
            )

        # 4. Comprobar si ya existe el Pull Request
        existing_pr = None
        for open_pr in self.repo.get_pulls(state='open', base=config.GITHUB_BASE_BRANCH):
            if open_pr.head.ref == branch_name:
                existing_pr = open_pr
                break
                
        if not existing_pr:
            # Crear el Pull Request solo si no existe
            existing_pr = self.repo.create_pull(
                title=f"[Agent] Metadata Proposal: {entity_name}",
                body=f"Sugerencia automática de gobierno para `{entity_name}` basada en documentación.",
                head=branch_name,
                base=config.GITHUB_BASE_BRANCH
            )

        return existing_pr.html_url