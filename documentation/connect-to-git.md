### Connect "sync-files" to a Git repository
<br>

You can synchronize your local folders to any Git server (GitHub, GitLab, Gitea, Bitbucket, or a self-hosted Git repository). With our multi-repository support, you can even sync different folders to entirely different Git repositories or branches!

#### 1. Create your remote Git repositories
- Go to your favorite Git provider (e.g., [GitHub New Repo](https://github.com/new) or GitLab).
- Create a new repository for your backup data (it can be Private or Public).
- **Tip**: Initialize the repository with an initial branch (typically named `main` or `master`), though empty repositories are also supported.

---

#### 2. Configure Authentication (`credentials/git_credentials.json`)

To keep sensitive credentials secure and separate from your general synchronization settings, configure your authentication method in a single dedicated credentials file. You can authenticate using either an **HTTPS Personal Access Token (PAT)** or an **SSH Key**.

<details>
<summary><b>Option A: HTTPS + Personal Access Token (Recommended for GitHub/GitLab)</b></summary>

##### Generating a Token on GitHub
1. Go to **Settings** → **Developer Settings** → **Personal access tokens** → **Tokens (classic)** (or open this [direct link](https://github.com/settings/tokens)).
2. Click **Generate new token (classic)**.
3. Select the `repo` scope (which gives write access to private and public repositories).
4. Generate and copy your token (e.g., `ghp_xxxxx...`).

##### Generating a Token on GitLab
1. Go to **Preferences** → **Access Tokens**.
2. Name your token and grant the `write_repository` or `api` scope.
3. Generate and copy the token.

##### Configuration file setup
Create a file named `git_credentials.json` inside the `credentials/` directory of this project:

```json
{
  "auth_type": "token",
  "username": "my-username",
  "token": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "author_name": "Sync Files Bot",
  "author_email": "sync-bot@local"
}
```
*(Note: This token will be automatically applied to any HTTPS Git repository URL configured in `config.yaml`).*
</details>

<details>
<summary><b>Option B: SSH Key</b></summary>

If you prefer SSH authentication, ensure your public SSH key is added to your GitHub/GitLab account or configured as a **Deploy Key** on the destination repository.

##### Configuration file setup
Create a file named `git_credentials.json` inside the `credentials/` directory of this project specifying your private key path:

```json
{
  "auth_type": "ssh",
  "ssh_key_path": "/home/username/.ssh/id_ed25519",
  "author_name": "Sync Files Bot",
  "author_email": "sync-bot@local"
}
```
*(Note: You can omit `"ssh_key_path"` if your operating system's SSH agent already loads the key automatically).*
</details>

---

#### 3. Configure your folders in `config.yaml`

Open `config.yaml` at the root of the project and define your synchronization rules using `cloud_provider: "Git"`. Each sync job specifies its own destination repository URL (`repository_url`) and target branch (`branch`):

```yaml
sync:
  - name: my_documents_backup
    cloud_provider: "Git"
    repository_url: "https://github.com/username/my-docs-backup.git" # or git@github.com:...
    branch: "main"     # Optional: target branch (defaults to 'main')
    sync_interval: 60  # in minutes
    compress: false    # Set to true to upload a single .zip archive instead of individual files
    local_path: "/home/username/Documents/Important"
    remote_path: "/backups/documents"  # Subfolder inside the destination Git repository
    exclude_patterns:  # works like a .gitignore file
      - "*.tmp"
      - ".DS_Store"

  - name: my_config_backup
    cloud_provider: "Git"
    repository_url: "https://github.com/username/my-dotfiles-backup.git"
    branch: "dev"
    sync_interval: 120
    compress: true
    local_path: "/home/username/.config"
    remote_path: "/"
```

#### How Git Synchronization Works Under the Hood
- On startup, the application clones a local working mirror of each configured repository into an excluded `.cache/git_repos/` directory.
- During scheduled sync operations, it compares file MD5 hashes to detect modifications without redundant I/O operations.
- New and modified files are staged (`git add`), committed with your designated author info (`git commit`), and pushed (`git push`) to the specified branch.
- Tokens and secrets are securely injected in memory during network communication and are never saved inside `.git/config` files on disk.
