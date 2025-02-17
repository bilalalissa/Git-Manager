# Git Manager

## Overview

Git Manager is a secure and interactive CLI tool for managing Git repositories. It allows users to:

- Initialize and configure Git repositories.
- Create new GitHub repositories directly from the CLI.
- Track and manage files.
- Enable auto-commit.
- Detect and commit changes automatically.
- Encrypt repository configurations for security.
- Enable daemon mode to run Git tracking in the background.
- View and edit local Git configurations.
- Remove files from Git tracking.
- Display tracked files and repository status.

## Features

- **Secure Configuration Storage:** Uses encryption to protect stored Git settings.
- **Interactive CLI Menu:** Provides a user-friendly interface for managing repositories.
- **Auto-Commit:** Tracks changes and commits them automatically.
- **Repository Setup:** Guides the user through Git remote configuration.
- **File Tracking:** Allows users to choose which files to track or remove from tracking.
- **Daemon Mode:** Runs Git tracking as a background process so it continues after exiting.
- **Git Configuration Management:** Allows users to view and edit Git settings with an option to cancel editing.
- **Create GitHub Repositories:** Users can create a new GitHub repository by providing a name, description, and privacy settings. The script now retrieves the GitHub username dynamically and correctly names the repository.
- **Show Tracked Files:** Users can list all tracked files in the repository.
- **Show Repository Status:** Users can check the current status of the Git repository.

## Installation

1. Ensure Git and Python 3 are installed.
2. Install dependencies using:
   ```bash
   pip install cryptography requests
   ```
3. Clone this repository or download `git_manager.py`.
4. Run the script:
   ```bash
   python git_manager.py
   ```

## Usage

Once the script runs, a menu will appear:

1. **Initialize Git Repository:** Detects if Git is initialized and sets up remote configuration if needed.
2. **Remove Git Configuration:** Deletes the Git configuration from the folder and resets the application settings.
3. **Create GitHub Repository:** Allows users to create a new GitHub repository directly from the app using the correct repository name and username.
4. **Show Git Configuration:** Displays current Git settings.
5. **Edit Git Configuration:** Modify local Git settings such as user name or email with an option to cancel.
6. **Remove Files from Tracking:** Remove specific files from Git tracking.
7. **Edit Application Settings:** Modify repository URL, toggle auto-commit, and enable/disable daemon mode.
8. **Reset Configuration:** Resets all saved configurations.
9. **Track Files:** Adds specific files or all files to tracking.
10. **Show Tracked Files:** Lists all files currently tracked in the repository.
11. **Show Repository Status:** Displays the current status of the Git repository.
12. **Exit:** Quit the program.

## Configuration Storage

- The script securely stores user settings in `tracked_files.json`, **encrypting** them using a generated key stored in `encryption.key`.
- The encryption ensures that repository details remain private and cannot be tampered with manually.

## Enabling Auto-Tracking (Daemon Mode)

The Git Manager can run automatically in the background to track changes:

- **Linux/macOS**: Uses `systemd` to run as a background service.
- **Windows**: Uses `Task Scheduler` to run tracking on system startup.

To enable daemon mode:

1. Open the **Git Manager** menu.
2. Select **Edit Application Settings**.
3. Toggle **Daemon Mode** (Enable/Disable).

To stop the daemon mode:

- **Linux/macOS**: Run:
  ```bash
  sudo systemctl stop git-tracker
  sudo systemctl disable git-tracker
  ```
- **Windows**: Run:
  ```bash
  schtasks /delete /tn GitTracker /f
  ```

## Notes

- If the `encryption.key` file is lost, the stored configuration cannot be decrypted.
- The auto-commit feature ensures that any tracked changes are committed and pushed automatically.
- Use the menu to manage configurations securely.

## Contributions

Contributions are welcome! Fork this repo, make improvements, and submit a pull request.

## License

This project is licensed under the MIT License.
# Git-Manager
