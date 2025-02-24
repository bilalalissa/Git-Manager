# EduTrack-ENSE477

ENSE 477 Capstone

In this file:

- Project Info
- Git Manager Info

~~ Git Manager ~~

# Git Manager

## Overview

Git Manager is a secure and interactive CLI tool for managing Git repositories. It allows users to:

- Initialize Git repositories.
- Set up remote repositories.
- Track and manage files.
- Enable auto-commit.
- Detect and commit changes automatically.
- Encrypt repository configurations for security.

## Features

- **Secure Configuration Storage:** Uses encryption to protect stored Git settings.
- **Interactive CLI Menu:** Provides a user-friendly interface for managing repositories.
- **Auto-Commit:** Tracks changes and commits them automatically.
- **Repository Setup:** Guides the user through Git remote configuration.
- **File Tracking:** Allows users to choose which files to track.

## Installation

1. Ensure Git and Python 3 are installed.
2. Install dependencies using:

   ```bash
   pip install cryptography requests
   ```
3. Clone this repository or download `git_manager.py`
4. Run the script:

   ```bash
   python git_manager.py
   ```

## Usage

Once the script runs, a menu will appear:

1. **Set Up Repository**: Enter a Git remote URL to configure the repository.
2. **Edit Configuration**: Modify repo URL or toggle auto-commit.
3. **Exit**: Quit the program.

## Configuration Storage

* The script securely stores user settings in `tracked_files.json`, **encrypting** them using a generated key stored in `encryption.key`.
* The encryption ensures that repository details remain private and cannot be tampered with manually.
* **Note**: Configuration files (`encryption.key`, `tracked_files.json`, and its backup) are automatically ignored by Git for security.

## Security Notes

- The `encryption.key` file is automatically generated and should never be shared or committed to version control.
- Configuration files are automatically excluded via `.gitignore` for security:
  - `encryption.key`: Contains the encryption key
  - `tracked_files.json`: Contains encrypted repository settings
  - `tracked_files.json.backup`: Backup of configuration file
- If the `encryption.key` file is lost, the stored configuration cannot be decrypted and will need to be reset.

## Auto-Commit Feature

- Auto-commit can be enabled through the "Edit Application Settings" menu
- When enabled, changes are automatically committed and pushed based on the configured interval
- Default interval is 30 minutes, but can be customized
- Status messages show when changes are detected and committed

## Notes

- If the `encryption.key` file is lost, the stored configuration cannot be decrypted.
- The auto-commit feature ensures that any tracked changes are committed and pushed automatically.
- Use the menu to manage configurations securely.

## Contributions

Contributions are welcome! Fork this repo, make improvements, and submit a pull request.

## License

This project is licensed under the MIT License.

## More about (Git Manager)

[ Code Technical Details ](https://)
