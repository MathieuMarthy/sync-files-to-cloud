# Sync Files to Cloud 🐢

A Python-based application that automatically synchronizes local folders to cloud storage providers on a scheduled
basis.

## Features

- **Automatic Synchronization**: Schedule periodic uploads of local folders to cloud storage
- **Multiple Folders**: Configure multiple folders with different sync intervals and settings
- **File Compression**: Optionally compress files before uploading to save storage space
- **Exclude Patterns**: Define patterns to exclude specific files or folders from sync
- **Desktop Notifications**: Get notified when reconnection to cloud provider is needed
- **Logging**: Comprehensive logging system to track all sync operations

## Supported Cloud Providers

| Provider     | Status         | Documentation                                           |
|--------------|----------------|---------------------------------------------------------|
| Google Drive | ✅ Available    | [Setup Guide](documentation/connect-to-google-drive.md) |
| OneDrive     | 🔜 Coming Soon | -                                                       |
| Dropbox      | 🔜 Coming Soon | -                                                       |

## Installation

1. Prerequisites

- Python 3.8 or higher

<br>

2. Clone the repository:

```bash
git clone <repository-url>
cd sync-files-to-cloud
```

3. Create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

4. Install required dependencies:

```bash
pip install -r requirements.txt
```

5. Set up cloud provider credentials:
    - For Google Drive: Follow the [Google Drive Setup Guide](documentation/connect-to-google-drive.md)
    - Place your `gdrive_credentials.json` file in the `credentials/` folder

## Configuration

Edit the `config.yaml` file to configure your synchronization settings:

```yaml
logging:
  level: "INFO"
  file_path: "app.log"

sync:
  - name: my_images
    cloud_provider: "GoogleDrive"
    sync_interval: 3600  # in seconds (3600 = 1 hour)
    compress: true
    local_path: "C:/Users/Username/Documents/Images"
    remote_path: "/images"
    exclude_patterns:
      - "*.tmp"
      - "temp_folder/*"
```

### Configuration Options

- **name**: Unique identifier for the sync folder
- **cloud_provider**: Cloud storage provider (currently only "GoogleDrive")
- **sync_interval**: Time between syncs in seconds
- **compress**: Whether to compress files into a zip archive before upload
- **local_path**: Absolute path to the local folder to sync
- **remote_path**: Destination path in the cloud storage
- **exclude_patterns**: List of patterns to exclude files (supports wildcards like `*.tmp`, `folder/*`)

## Usage

Run the application:

```bash
python main.py
```

The application will:

1. Initialize connections to configured cloud providers
2. Perform an initial sync for all configured folders
3. Schedule periodic syncs based on the configured intervals
4. Continue running until stopped (Ctrl+C)

### Running at Startup

To automatically run the script when your computer starts:

<details>
<summary>Windows Instructions</summary>
1. Create a batch file `start_sync.bat` in the project directory:

```batch
@echo off
cd /d C:\path\to\sync-files-to-cloud
call venv\Scripts\activate
python main.py
```

2. Press `Win + R`, type `shell:startup`, and press Enter
3. Create a shortcut to `start_sync.bat` in the Startup folder
4. (Optional) Right-click the shortcut → Properties → Run: Minimized

</details>


<details>
<summary>Linux Instructions (systemd)</summary>

1. Create a systemd service file `/etc/systemd/system/sync-files.service`:

```ini
[Unit]
Description = Sync Files to Cloud
After = network.target

[Service]
Type = simple
User = your-username
WorkingDirectory = /path/to/sync-files-to-cloud
ExecStart = /path/to/sync-files-to-cloud/venv/bin/python main.py
Restart = on-failure

[Install]
WantedBy = multi-user.target
```

2. Enable and start the service:

```bash
sudo systemctl enable sync-files.service
sudo systemctl start sync-files.service
```

</details>

## How It Works

1. **Configuration Loading**: The application reads `config.yaml` to load sync parameters
2. **Cloud Authentication**: Connects to cloud providers using credentials from the `credentials/` folder
3. **File Discovery**: Scans local folders and filters files based on exclude patterns
4. **Compression** (optional): Compresses files into a zip archive
5. **Upload**: Uploads files to the cloud provider while preserving folder structure
6. **Scheduling**: Repeats the process at configured intervals
7. **Error Handling**: If connection fails, sends desktop notification to reconnect

## Troubleshooting

### Files Not Syncing

- Check that the local path exists and is accessible
- Verify exclude patterns are not blocking desired files
- Review logs in `app.log` for detailed error messages

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.
