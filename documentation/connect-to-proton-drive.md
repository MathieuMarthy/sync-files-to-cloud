### Connect "sync-files" to Proton Drive
<br>

You can synchronize your local folders and files to **Proton Drive** with end-to-end encryption (E2EE). Because Proton Drive encrypts all files on the client side before uploading, our application interfaces with the **official Proton Drive CLI** (recommended) or optionally **Rclone**.

---

#### 1. Choose your Backend & Install the CLI

<details open>
<summary><b>Option A: Official Proton Drive CLI (Recommended)</b></summary>

The official Proton Drive CLI is developed by Proton, built on their official SDK, and supports client-side encryption natively.

##### Installation
1. Download the official **Proton Drive CLI** binary for your operating system:
   - Go to the [Proton Drive Download Page](https://proton.me/drive/download#desktop) or check the [official SDK releases](https://github.com/ProtonDriveApps/sdk).
2. Extract the binary and place it in your system's `PATH`:
   - **Linux / macOS**: Move `proton-drive` to `/usr/local/bin/` or `~/.local/bin/` and make it executable (`chmod +x proton-drive`).
   - **Windows**: Place `proton-drive.exe` in a folder included in your system `PATH` (e.g., `C:\Program Files\ProtonDriveCLI\`).
3. Verify the installation in your terminal:
   ```bash
   proton-drive --help
   ```

##### Initial Authentication
Run the login command in your terminal to authenticate with your Proton account:
```bash
proton-drive auth login
```
This will open your default browser to authorize the session. Your credentials and session tokens will be stored securely in your operating system's native secret store (Windows Credential Manager, macOS Keychain, or `libsecret` on Linux).

> [!NOTE]
> **Headless Linux / SSH sessions**: If running on a headless server without an active X11/Wayland display, you can run:
> ```bash
> dbus-run-session -- proton-drive auth login
> ```

</details>

<details>
<summary><b>Option B: Rclone Backend (Alternative for power users)</b></summary>

If you already use Rclone with the `protondrive` backend:

1. Ensure Rclone is installed on your machine:
   ```bash
   rclone version
   ```
2. Configure a Proton Drive remote named `protondrive`:
   ```bash
   rclone config
   ```
   Follow the prompts to select `protondrive` and log in with your credentials.
3. Verify your configuration:
   ```bash
   rclone lsf protondrive:
   ```

</details>

---

#### 2. Optional: Configure Custom CLI Settings (`credentials/protondrive_credentials.json`)

If `proton-drive` is already in your system `PATH`, **no credentials file is required**! The program will detect and use it automatically.

If you have installed the CLI in a non-standard location or want to customize upload behavior, create `credentials/protondrive_credentials.json`:

```json
{
  "backend": "official_cli",
  "cli_path": "/chemin/personnalise/vers/proton-drive",
  "conflict_strategy": "replace"
}
```

Available `conflict_strategy` options:
- `"replace"` *(default)*: Replaces (trashes) the remote file or folder and uploads the local copy.
- `"create-new-revision"`: Creates a new revision of the existing file on Proton Drive.
- `"rename"`: Adds a unique suffix to the file name if a conflict occurs.
- `"skip"`: Skips uploading the conflicting file.


For Rclone users, configure:
```json
{
  "backend": "rclone",
  "rclone_path": "rclone",
  "rclone_remote": "protondrive"
}
```

---

#### 3. Update `config.yaml`

Add your folder configuration under the `sync` section in `config.yaml`:

```yaml
sync:
  - name: my_proton_documents
    cloud_provider: "ProtonDrive"
    sync_interval: 60  # in minutes
    compress: true     # Recommended: compresses into a single zip archive before E2EE upload
    local_path: "/home/user/Documents/ProtonBackup"
    remote_path: "/Backups/Documents"
    exclude_patterns:
      - "*.tmp"
      - ".git/*"
```

You can also sync uncompressed folders to preserve individual file structure:

```yaml
sync:
  - name: my_uncompressed_folder
    cloud_provider: "ProtonDrive"
    sync_interval: 120
    compress: false
    local_path: "/home/user/Work"
    remote_path: "/Work"
    exclude_patterns:
      - "node_modules/*"
      - "*.log"
```

---

#### 4. Run the Application

Start the synchronization engine:
```bash
python main.py
```

If your session ever expires, the application will send a desktop notification with a **Reconnect** button allowing you to re-authenticate seamlessly.
