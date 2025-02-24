# Git Manager

## Overview

Git Manager is a secure and interactive CLI tool for managing Git repositories. It allows users to:

- Initialize and configure Git repositories
- Create new GitHub repositories directly from the CLI
- Track and manage files with pattern matching
- Enable auto-commit and daemon mode
- Detect and commit changes automatically
- Encrypt repository configurations for security
- Resolve merge conflicts interactively
- Create and restore configuration backups
- Monitor repository health and status
- View detailed operation logs

## Features

- **Secure Configuration Storage:** Uses encryption to protect stored Git settings
- **Interactive CLI Menu:** User-friendly interface for managing repositories
- **Advanced File Tracking:** 
  - Track specific files
  - Track by pattern (e.g., *.py)
  - Track all files
  - Remove files from tracking
- **Auto-Commit & Daemon Mode:**
  - Automatic change detection
  - Configurable commit intervals
  - Background operation support
- **Conflict Resolution:**
  - Interactive conflict resolution
  - View file differences
  - Choose between local/remote versions
  - Manual editing support
- **Backup Management:**
  - Create configuration backups
  - List available backups
  - Restore from backup
- **Status Monitoring:**
  - Detailed repository health check
  - Local and remote status
  - Performance metrics
- **Operation Logging:**
  - Comprehensive operation logs
  - Error tracking and reporting
  - Success/failure notifications

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
14. Resolve Conflicts
15. Backup Management
16. Detailed Status
17. Exit

## Configuration Storage

- Settings stored in `tracked_files.json`, encrypted using `encryption.key`
- Configuration files automatically ignored by Git for security
- Logs stored in `git_manager.log` for troubleshooting
- Backup system for configuration recovery

## Backup System

The backup system allows you to:
- Create snapshots of your configuration
- View all available backups
- Restore from any previous backup
- Maintain configuration history

## Conflict Resolution

The interactive conflict resolution system helps you:
- Identify conflicting files
- View differences between versions
- Choose between local and remote changes
- Edit files manually when needed
- Track resolution progress

## Status Monitoring

Detailed status checks provide:
- Local change tracking
- Remote synchronization status
- Repository health metrics
- Performance measurements

## Notes

- If `encryption.key` is lost, stored configuration cannot be decrypted
- Auto-commit ensures tracked changes are committed automatically
- Use the menu to manage configurations securely
- Check logs (Option 13) when errors occur
- Create regular backups of your configuration

## Contributions

Contributions are welcome! Please fork and submit pull requests.

## License

This project is licensed under the MIT License.
