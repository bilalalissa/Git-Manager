# Git Manager

## Overview

Git Manager is a secure and interactive CLI tool for managing Git repositories. It allows users to:

- Initialize and configure Git repositories
- Create new GitHub repositories directly from the CLI
- Track and manage files
- Enable auto-commit
- Detect and commit changes automatically
- Encrypt repository configurations for security
- Enable daemon mode to run Git tracking in the background
- View and edit local Git configurations
- Remove files from Git tracking
- Display tracked files and repository status

## Features

- **Secure Configuration Storage:** Uses encryption to protect stored Git settings
- **Interactive CLI Menu:** Provides a user-friendly interface for managing repositories
- **Auto-Commit:** Tracks changes and commits them automatically
- **Repository Setup:** Guides the user through Git remote configuration
- **File Tracking:** Allows users to choose which files to track or remove from tracking
- **Daemon Mode:** Runs Git tracking as a background process
- **Git Configuration Management:** View and edit Git settings with cancel option
- **Create GitHub Repositories:** Create repositories directly from CLI
- **Show Tracked Files:** List all tracked files in the repository
- **Show Repository Status:** Check current Git repository status

## Installation

1. Ensure Git and Python 3 are installed
2. Install dependencies:
   ```bash
   pip install cryptography requests
   ```
3. Clone this repository or download `git_manager.py`
4. Run the script:
   ```bash
   python git_manager.py
   ```

## Usage

The menu provides the following options:

1. Track Files
2. Show Tracked Files
3. Remove Files from Tracking

4. Show Git Configuration
5. Edit Git Configuration

6. Edit Application Settings
7. Reset Git Manager Configuration

8. Initialize Git Repository
9. Remove Git Configuration
10. Create GitHub Repository
11. Show Repository Status
12. Sync with Remote
13. Show Recent Logs
14. Exit

## Configuration Storage

- Settings stored in `tracked_files.json`, encrypted using `encryption.key`
- Configuration files automatically ignored by Git for security
- Logs stored in `git_manager.log` for troubleshooting

## Enabling Auto-Tracking (Daemon Mode)

The Git Manager can run automatically in the background:

- **Linux/macOS**: Uses `systemd` service
- **Windows**: Uses Task Scheduler

To enable daemon mode:
1. Select "Edit Application Settings"
2. Toggle "Daemon Mode"

## Notes

- If `encryption.key` is lost, stored configuration cannot be decrypted
- Auto-commit ensures tracked changes are committed automatically
- Use the menu to manage configurations securely

## Contributions

Contributions are welcome! Please fork and submit pull requests.

## License

This project is licensed under the MIT License.
