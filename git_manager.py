import os
import json
import subprocess
import time
import base64
import sys
from cryptography.fernet import Fernet
import platform
import requests
import logging
from datetime import datetime
from backup_manager import BackupManager
import glob
import fnmatch

CONFIG_FILE = "tracked_files.json"
ENCRYPTION_KEY_FILE = "encryption.key"
SERVICE_FILE = "/etc/systemd/system/git-tracker.service" if platform.system() == "Linux" else "git-tracker.bat"
GITHUB_API_URL = "https://api.github.com/user/repos"

BACKUP_MANAGER = BackupManager(CONFIG_FILE, ENCRYPTION_KEY_FILE)

def generate_key():
    """Generates and saves an encryption key if it doesn't exist."""
    if not os.path.exists(ENCRYPTION_KEY_FILE):
        key = Fernet.generate_key()
        with open(ENCRYPTION_KEY_FILE, "wb") as key_file:
            key_file.write(key)

def load_key():
    """Loads the encryption key from file."""
    if not os.path.exists(ENCRYPTION_KEY_FILE):
        generate_key()
    with open(ENCRYPTION_KEY_FILE, "rb") as key_file:
        return key_file.read()

def encrypt_data(data):
    """Encrypts data using the encryption key."""
    key = load_key()
    cipher = Fernet(key)
    return cipher.encrypt(json.dumps(data).encode()).decode()

def decrypt_data(encrypted_data):
    """Decrypts encrypted data using the encryption key."""
    key = load_key()
    cipher = Fernet(key)
    return json.loads(cipher.decrypt(encrypted_data.encode()).decode())

def load_config():
    """Loads and decrypts configuration from the JSON file."""
    if not os.path.exists(CONFIG_FILE):
        return {"repo_url": "", "tracked_files": [], "auto_commit": False, "daemon_mode": False}
    try:
        with open(CONFIG_FILE, "r") as file:
            encrypted_data = file.read()
            config = decrypt_data(encrypted_data)
            # Ensure all expected keys exist
            if "daemon_mode" not in config:
                config["daemon_mode"] = False
            if "tracked_files" not in config:
                config["tracked_files"] = []
            return config
    except (json.JSONDecodeError, ValueError):
        print("\nError reading configuration file. Resetting to default.\n")
        return {"repo_url": "", "tracked_files": [], "auto_commit": False, "daemon_mode": False}

def save_config(config):
    """Encrypts and saves configuration securely."""
    try:
        with open(CONFIG_FILE, "w") as file:
            file.write(encrypt_data(config))
    except Exception as e:
        print(f"\nError saving configuration: {e}\n")

def reset_config():
    """Resets Git Manager configuration to defaults."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    print("\n\t== >Git Manager configuration has been reset.\n")

def check_gitignore(file_name):
    """Checks if a file is in .gitignore."""
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            ignored = f.read().splitlines()
            # Check direct matches and patterns
            for pattern in ignored:
                if pattern and not pattern.startswith("#"):
                    if file_name == pattern or fnmatch.fnmatch(file_name, pattern):
                        return True
    return False

def track_files():
    """Enhanced file tracking with pattern support and status feedback."""
    config = load_config()
    print("\nCurrent tracking mode:", "All files" if config["tracked_files"] == "all" else "Selected files")
    if isinstance(config["tracked_files"], list):
        print("Currently tracked files:", ", ".join(config["tracked_files"]) or "None")
    
    while True:
        print("\nTracking options:")
        print("1. Track specific file")
        print("2. Track by pattern (e.g., *.py)")
        print("3. Track all files")
        print("4. Done")
        
        choice = input("\nSelect option: ")
        if choice == "1":
            file_name = input("Enter file name: ")
            if os.path.exists(file_name):
                if check_gitignore(file_name):
                    print(f"\nWarning: {file_name} is in .gitignore")
                    confirm = input("Do you still want to track this file? (y/n): ")
                    if confirm.lower() != 'y':
                        continue
                if isinstance(config["tracked_files"], list):
                    if file_name not in config["tracked_files"]:
                        config["tracked_files"].append(file_name)
                        print(f"Added {file_name} to tracking")
                        log_operation("Tracking", "SUCCESS", f"Added {file_name}")
                        save_config(config)
                    else:
                        print(f"{file_name} is already being tracked")
                else:
                    print("All files are currently being tracked")
            else:
                print("File not found")
                log_operation("Tracking", "ERROR", f"File not found: {file_name}")
        elif choice == "2":
            pattern = input("Enter file pattern (e.g., *.py): ")
            matched_files = glob.glob(pattern)
            if matched_files:
                print(f"\nFound {len(matched_files)} matching files:")
                for file in matched_files[:5]:
                    print(f"- {file}")
                if len(matched_files) > 5:
                    print(f"... and {len(matched_files)-5} more")
                confirm = input("\nAdd these files to tracking? (y/n): ")
                if confirm.lower() == 'y':
                    config["tracked_files"].extend(matched_files)
                    log_operation("Tracking", "SUCCESS", f"Added {len(matched_files)} files matching {pattern}")
            else:
                print("No files match the pattern")
                log_operation("Tracking", "WARNING", f"No files match pattern: {pattern}")
        elif choice == "3":
            config["tracked_files"] = "all"
            print("Now tracking all files")
            log_operation("Tracking", "SUCCESS", "Switched to tracking all files")
        elif choice == "4":
            break
    
    save_config(config)

def edit_config():
    """Allows user to modify the encrypted JSON configuration."""
    config = load_config()
    print("\nEdit Configuration:")
    print(f"1. Auto-Commit: {'Enabled' if config['auto_commit'] else 'Disabled'}")
    print(f"2. Daemon Mode: {'Enabled' if config['daemon_mode'] else 'Disabled'}")
    print(f"3. Commit Interval: {config.get('commit_interval', 30)} minutes")
    choice = input("\nEnter the number of the setting to edit (or 'q' to quit): ")
    
    try:
        if choice == "1":
            # Toggle auto-commit
            config["auto_commit"] = not config["auto_commit"]
            
            if config["auto_commit"]:  # If enabling auto-commit
                interval = input("\nEnter commit interval in minutes (default: 30): ") or "30"
                try:
                    config["commit_interval"] = int(interval)
                except ValueError:
                    print("\nInvalid interval. Using default 30 minutes")
                    config["commit_interval"] = 30
                
                # Save configuration first
                if save_config(config):
                    print(f"\nAuto-Commit enabled with {config['commit_interval']} minute intervals")
                    
                    # Start auto-commit thread
                    import threading
                    auto_commit_thread = threading.Thread(target=auto_commit_process, daemon=True)
                    auto_commit_thread.start()
                else:
                    # Revert changes if save failed
                    config["auto_commit"] = False
                    print("\nFailed to save configuration. Auto-commit not enabled.")
                    log_operation("Configuration", "ERROR", "Failed to save auto-commit settings")
            else:  # If disabling auto-commit
                if save_config(config):
                    print("\nAuto-Commit disabled")
                    log_operation("Configuration", "SUCCESS", "Auto-commit disabled")
                else:
                    # Revert changes if save failed
                    config["auto_commit"] = True
                    print("\nFailed to save configuration")
                    log_operation("Configuration", "ERROR", "Failed to save auto-commit settings")
            
        elif choice == "2":
            try:
                old_value = config.get("daemon_mode", False)
                config["daemon_mode"] = not old_value
                
                if save_config(config):
                    new_state = "Enabled" if config["daemon_mode"] else "Disabled"
                    print(f"\nDaemon Mode {new_state}")
                    log_operation("Configuration", "SUCCESS", f"Daemon mode {new_state.lower()}")
                else:
                    config["daemon_mode"] = old_value
                    print("\nFailed to save daemon mode configuration")
                    log_operation("Configuration", "ERROR", "Failed to save daemon mode settings")
            except Exception as e:
                print(f"\nError updating daemon mode: {str(e)}")
                log_operation("Configuration", "ERROR", f"Daemon mode error: {str(e)}")
            
        elif choice == "3" and config["auto_commit"]:
            old_interval = config.get("commit_interval", 30)
            try:
                interval = input("\nEnter new commit interval in minutes: ")
                new_interval = int(interval)
                if new_interval > 0:
                    config["commit_interval"] = new_interval
                    if save_config(config):
                        print(f"\nCommit interval updated to {new_interval} minutes")
                        log_operation("Configuration", "SUCCESS", f"Commit interval set to {new_interval} minutes")
                    else:
                        config["commit_interval"] = old_interval
                        print("\nFailed to save configuration")
                        log_operation("Configuration", "ERROR", "Failed to save commit interval")
                else:
                    print("\nInterval must be greater than 0")
                    log_operation("Configuration", "ERROR", "Invalid commit interval value")
            except ValueError:
                print("\nInvalid interval. Keeping current setting.")
                log_operation("Configuration", "ERROR", "Invalid commit interval format")

        elif choice == "q":
            # Return to main menu
            print("\n")
            return
        
        else:
            print("\nInvalid choice.")
            return
            
    except Exception as e:
        print(f"\nError updating configuration: {str(e)}")
        log_operation("Configuration", "ERROR", f"Configuration update error: {str(e)}")

def show_git_config():
    """Displays local Git configuration."""
    config_data = subprocess.run("git config --list", shell=True, capture_output=True, text=True).stdout.strip()
    print("\nCurrent Git Configuration:")
    print(config_data)
    print("\n")

def edit_git_config():
    """Allows user to edit Git configuration settings with a cancel option."""
    while True:
        key = input("\nEnter the Git config key you want to modify \n(e.g., user.name, user.email) \nor type 'cancel' to exit: ")
        if key.lower() == "cancel":
            print("\nEdit Git Configuration canceled.\n")
            return
        value = input(f"\nEnter the new value for {key}: ")
        subprocess.run(f"\ngit config --global {key} \"{value}\"", shell=True)
        print(f"\nUpdated {key} to {value}\n")

def remove_from_tracking():
    """Allows user to remove files from Git tracking."""
    config = load_config()
    while True:
        file_name = input("\nEnter file to remove from tracking (or type 'done' to finish): ")
        if file_name.lower() == "done":
            break
            
        if file_name in config["tracked_files"]:
            config["tracked_files"].remove(file_name)
            subprocess.run(f"git rm --cached {file_name}", shell=True)
            print(f" - Removed {file_name} from tracking.")
            log_operation("Tracking", "SUCCESS", f"Removed {file_name} from tracking")
        else:
            print(f" - {file_name} is not in tracking list.")
            
    # Save the updated configuration
    if save_config(config):
        subprocess.run('git commit -m "Removed files from tracking"', shell=True)
        subprocess.run("git push origin main", shell=True)
        print("\nChanges saved and committed successfully")
    else:
        print("\nFailed to save tracking changes")
        log_operation("Tracking", "ERROR", "Failed to save tracking changes")

def remove_git_config():
    """Removes Git configuration from the folder and the application settings."""
    confirm = input("Are you sure you want to remove the Git configuration from this folder? (y/n): ")
    if confirm.lower() == "y":
        subprocess.run("rm -rf .git", shell=True)
        reset_config()
        print("\nGit configuration has been removed from the folder \nand the application.\n")
        print("You can initialize a new repository using option 8 or")
        print("create a new GitHub repository using option 10.\n")
    else:
        print("\nRemoval cancelled.\n")

def create_github_repo():
    """Allows the user to create a new repository on GitHub with a proper name."""
    config = load_config()
    github_token = config.get("github_token")
    if not github_token:
        github_token = input("\nEnter your GitHub personal access token: ")
        config["github_token"] = github_token
        save_config(config)
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    username_response = requests.get("https://api.github.com/user", headers=headers)
    if username_response.status_code == 200:
        username = username_response.json().get("login")
    else:
        print("\n\tFailed to retrieve GitHub username. Check your token.\n")
        return
    repo_name = input("\nEnter a name for your new GitHub repository: ")
    description = input("\nEnter a description for the repository: ")
    private = input("\nShould the repository be private? (y/n): ").strip().lower() == 'y'
    data = {"name": repo_name, "description": description, "private": private}
    response = requests.post(GITHUB_API_URL, json=data, headers=headers)
    if response.status_code == 201:
        repo_url = f"https://github.com/{username}/{repo_name}.git"
        print(f"Repository created successfully: {repo_url}")
        config["repo_url"] = repo_url
        save_config(config)
    else:
        print(f"\n\tFailed to create repository: {response.json()}\nCheck your GitHub token permissions.\n")

def show_tracked_files():
    """Displays all files currently being tracked."""
    config = load_config()
    print("\nCurrently tracked files:")
    if config["tracked_files"] == "all":
        print("All files in repository (except those in .gitignore)")
        # Show actual tracked files from git, excluding those in .gitignore
        result = subprocess.run(
            "git ls-files",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            ignored_files = set()
            if os.path.exists(".gitignore"):
                with open(".gitignore", "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            ignored_files.add(line)
            
            for file in result.stdout.splitlines():
                if not any(fnmatch.fnmatch(file, pattern) for pattern in ignored_files):
                    print(f"- {file}")
    else:
        if not config["tracked_files"]:
            print("No files are currently being tracked")
        else:
            for file in config["tracked_files"]:
                if os.path.exists(file):
                    status = "✓" if verify_tracked_file(file) else "!"
                    print(f"- {file} {status}")
                else:
                    print(f"- {file} (missing)")
    print()

def show_repo_status():
    """Displays the current Git repository status."""
    repo_status = subprocess.run("git status", shell=True, capture_output=True, text=True).stdout.strip()
    print("\nRepository Status:")
    print(repo_status)
    print("\n")

def auto_commit_process():
    """Handles automatic commits and pushes for tracked files only"""
    log_operation("Auto-commit", "INFO", "Process started")
    error_count = 0
    has_errors = False
    
    # Configure Git pull strategy silently
    try:
        subprocess.run(
            "git config pull.rebase false",
            shell=True,
            check=True,
            capture_output=True
        )
    except Exception:
        pass
    
    while True:
        try:
            config = load_config()
            # Check both auto-commit and daemon mode
            if not (config.get("auto_commit") or config.get("daemon_mode")):
                return
                
            # Get list of tracked files
            tracked_files = config.get("tracked_files", [])
            if not tracked_files:
                time.sleep(config.get("commit_interval", 30) * 60)
                continue
                
            # Check for changes in tracked files only
            changes_detected = False
            
            if tracked_files == "all":
                status = subprocess.run(
                    "git status --porcelain",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                changes_detected = bool(status.stdout.strip())
            else:
                for file in tracked_files:
                    if os.path.exists(file):
                        file_status = subprocess.run(
                            f"git status --porcelain {file}",
                            shell=True,
                            capture_output=True,
                            text=True
                        )
                        if file_status.stdout.strip():
                            changes_detected = True
                            break
            
            if changes_detected:
                try:
                    # First, fetch to check for remote changes
                    subprocess.run(
                        "git fetch origin",
                        shell=True,
                        check=True,
                        timeout=30,
                        capture_output=True
                    )
                    
                    # Stage only tracked files
                    if tracked_files == "all":
                        subprocess.run(
                            "git add .",
                            shell=True,
                            check=True,
                            timeout=30,
                            capture_output=True
                        )
                    else:
                        for file in tracked_files:
                            if os.path.exists(file):
                                subprocess.run(
                                    f"git add {file}",
                                    shell=True,
                                    check=True,
                                    timeout=30,
                                    capture_output=True
                                )
                    
                    # Check if we have changes to commit
                    status = subprocess.run(
                        "git status --porcelain",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    
                    if status.stdout.strip():
                        # Commit changes
                        subprocess.run(
                            'git commit -m "Auto-commit: Changes in tracked files"',
                            shell=True,
                            check=True,
                            timeout=30,
                            capture_output=True
                        )
                        
                        # Try to pull first to avoid conflicts
                        try:
                            subprocess.run(
                                "git pull --no-rebase origin main",
                                shell=True,
                                check=True,
                                timeout=30,
                                capture_output=True
                            )
                        except:
                            pass
                        
                        # Push changes
                        subprocess.run(
                            "git push origin main",
                            shell=True,
                            check=True,
                            timeout=30,
                            capture_output=True
                        )
                        
                        log_operation("Auto-commit", "SUCCESS", "Changes committed and pushed")
                        error_count = 0
                    
                except subprocess.TimeoutExpired:
                    error_count += 1
                    log_operation("Auto-commit", "ERROR", f"Timeout error (attempt {error_count}/3)")
                    has_errors = True
                    if error_count >= 3:
                        log_operation("Auto-commit", "ERROR", "Process stopped due to timeouts")
                        print("\nAuto-commit stopped. Check logs (Option 13) for details.")
                        return
                    continue
                    
                except subprocess.CalledProcessError as e:
                    error_count += 1
                    log_operation("Auto-commit", "ERROR", f"Git error: {str(e)}")
                    has_errors = True
                    if error_count >= 3:
                        log_operation("Auto-commit", "ERROR", "Process stopped due to repeated errors")
                        print("\nAuto-commit stopped. Check logs (Option 13) for details.")
                        return
                    continue
            
            # If there were errors, notify user to check logs
            if has_errors:
                print("\nSome operations had errors. Use Option 13 to view details.")
                has_errors = False
                
            # Wait interval
            interval = config.get("commit_interval", 30)
            time.sleep(interval * 60)
            
        except Exception as e:
            log_operation("Auto-commit", "ERROR", f"Unexpected error: {str(e)}")
            error_count += 1
            has_errors = True
            if error_count >= 3:
                log_operation("Auto-commit", "ERROR", "Process stopped due to repeated errors")
                print("\nAuto-commit stopped. Check logs (Option 13) for details.")
                return
            time.sleep(300)

def verify_git_repo():
    """Verifies the Git repository is properly initialized and configured."""
    try:
        # Check if .git exists
        if not os.path.exists(".git"):
            return False, "No Git repository found"

        # Check if git commands work
        status_result = subprocess.run(
            "git status",
            shell=True,
            capture_output=True,
            text=True
        )
        if status_result.returncode != 0:
            return False, "Invalid Git repository"

        # Check remote configuration
        config = load_config()
        if config.get("repo_url"):
            remote_result = subprocess.run(
                "git remote -v",
                shell=True,
                capture_output=True,
                text=True
            )
            if config["repo_url"] not in remote_result.stdout:
                return False, "Remote configuration mismatch"

        return True, "Repository properly configured"

    except Exception as e:
        return False, f"Error verifying repository: {str(e)}"

def sync_with_remote():
    """Syncs local repository with remote and handles merges."""
    try:
        print("\n=== Syncing with Remote Repository ===")
        
        # Check if repository exists and has a remote
        if not os.path.exists(".git"):
            print("No Git repository found in current directory.")
            return
            
        remote_check = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
        if not remote_check.stdout:
            print("No remote repository configured.")
            return

        # Fetch latest changes
        print("\nFetching remote changes...")
        fetch_result = subprocess.run("git fetch origin", shell=True, capture_output=True, text=True)
        if fetch_result.returncode != 0:
            print(f"Error fetching changes: {fetch_result.stderr}")
            return

        # Check if we're behind remote
        status = subprocess.run(
            "git status -uno",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if "Your branch is behind" in status.stdout:
            print("\nLocal repository is behind remote. Changes detected.")
            
            # Check for local changes
            local_changes = subprocess.run(
                "git status --porcelain",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if local_changes.stdout:
                print("\nLocal changes detected. Choose how to proceed:")
                print("1. Stash local changes and pull")
                print("2. Merge remote changes (might cause conflicts)")
                print("3. Cancel sync")
                
                choice = input("\nEnter your choice (1-3): ")
                
                if choice == "1":
                    # Stash local changes
                    subprocess.run("git stash", shell=True, check=True)
                    print("\nLocal changes stashed.")
                    
                    # Pull changes
                    pull_result = subprocess.run("git pull origin main", shell=True, capture_output=True, text=True)
                    if pull_result.returncode == 0:
                        print("\nSuccessfully pulled remote changes.")
                        
                        # Try to apply stash
                        stash_result = subprocess.run("git stash pop", shell=True, capture_output=True, text=True)
                        if stash_result.returncode == 0:
                            print("Local changes reapplied successfully.")
                        else:
                            print("\nConflicts occurred while reapplying local changes.")
                            print("Your changes are saved in the stash. Use 'git stash list' to see them.")
                            print("Resolve conflicts manually when ready using 'git stash pop'")
                    else:
                        print(f"\nError pulling changes: {pull_result.stderr}")
                        
                elif choice == "2":
                    # Try to merge directly
                    merge_result = subprocess.run("git pull origin main", shell=True, capture_output=True, text=True)
                    if merge_result.returncode == 0:
                        print("\nMerge successful!")
                    else:
                        print("\nMerge conflicts occurred. Please resolve them manually:")
                        print("1. Fix conflicts in the affected files")
                        print("2. Use 'git add' to mark them as resolved")
                        print("3. Use 'git commit' to finish the merge")
                        
                elif choice == "3":
                    print("\nSync cancelled.")
                    return
                    
            else:
                # No local changes, safe to pull
                pull_result = subprocess.run("git pull origin main", shell=True, capture_output=True, text=True)
                if pull_result.returncode == 0:
                    print("\nSuccessfully pulled remote changes.")
                else:
                    print(f"\nError pulling changes: {pull_result.stderr}")
        else:
            print("\nLocal repository is up to date with remote.")

    except Exception as e:
        print(f"\nError during sync: {str(e)}")

def verify_config_files():
    """Verifies configuration files exist and are accessible."""
    print("\nChecking configuration files:")
    
    # Check encryption key
    if os.path.exists(ENCRYPTION_KEY_FILE):
        print("- encryption.key: Found")
    else:
        print("- encryption.key: Missing (will be created)")
        generate_key()
    
    # Check configuration file
    if os.path.exists(CONFIG_FILE):
        print("- tracked_files.json: Found")
        try:
            config = load_config()
            print("  Status: Readable")
        except Exception as e:
            print(f"  Status: Error reading ({str(e)})")
    else:
        print("- tracked_files.json: Not created yet")
        print("  (File will be created when saving settings)")

def initialize_git():
    """Initializes a local Git repository and configures remote if needed."""
    if os.path.exists(".git"):
        print("\nGit repository already initialized in this folder.\n")
        return

    confirm = input("\n\tNo Git repository found. \nDo you want to initialize one? (y/n): ")
    if confirm.lower() != "y":
        print("\nRepository initialization cancelled.\n")
        return

    try:
        # Generate new encryption key and config files
        if os.path.exists(ENCRYPTION_KEY_FILE):
            os.remove(ENCRYPTION_KEY_FILE)
        generate_key()
        print("\n- Generated new encryption key")

        # Initialize local repository
        subprocess.run("git init", shell=True, check=True)
        subprocess.run("git branch -M main", shell=True, check=True)
        print("- Local repository initialized")
        
        # Configure remote if needed
        configure_remote = input("\nDo you want to configure a remote repository? (y/n): ")
        if configure_remote.lower() == "y":
            remote_url = input("\nEnter remote repository URL: ").strip()
            if remote_url:
                try:
                    # Add remote
                    subprocess.run(f"git remote add origin {remote_url}", shell=True, check=True)
                    print("- Remote repository configured")
                    
                    # Save new configuration
                    config = load_config()
                    config["repo_url"] = remote_url
                    
                    # Direct save without retries
                    with open(CONFIG_FILE, "w", encoding='utf-8') as file:
                        file.write(encrypt_data(config))
                    print("- Configuration saved")
                    
                except Exception as e:
                    print(f"\nError configuring remote: {str(e)}")
                    return
        
        print("\n=== Repository Setup Complete ===")
        print("- Local repository: Initialized")
        print("- Default branch: main")
        print("- Encryption: New key generated")
        if configure_remote.lower() == "y":
            print("- Remote repository: Configured")
        print("\nYou can now start tracking files and making commits.\n")

    except Exception as e:
        print(f"\nError during initialization: {str(e)}")
        # Cleanup if initialization failed
        if os.path.exists(".git"):
            import shutil
            shutil.rmtree(".git")
        if os.path.exists(ENCRYPTION_KEY_FILE):
            os.remove(ENCRYPTION_KEY_FILE)
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        print("Repository initialization failed. Please try again.\n")

def menu():
    """Displays the interactive menu."""
    setup_logging()
    generate_key()
    verify_config_files()
    
    # Start auto-commit thread if either auto-commit or daemon mode is enabled
    config = load_config()
    if config.get("auto_commit") or config.get("daemon_mode"):
        import threading
        auto_commit_thread = threading.Thread(target=auto_commit_process, daemon=True)
        auto_commit_thread.start()
    
    show_welcome = True
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Verify repository status
    repo_valid, repo_message = verify_git_repo()
    if not repo_valid:
        print(f"\nWarning: {repo_message}")
        print("Use option 8 to initialize repository if needed.\n")
    
    if show_welcome:
        print("\n\t==  Welcome to Git Manager  ==\n")
        show_welcome = False
        
    while True:
        print("\nGit Manager Menu:")
        print("1. Track Files")
        print("2. Show Tracked Files")
        print("3. Remove Files from Tracking\n")
        print("4. Show Git Configuration")
        print("5. Edit Git Configuration\n")
        print("6. Edit Application Settings")
        print("7. Reset Git Manager Configuration\n")
        print("8. Initialize Git Repository")
        print("9. Remove Git Configuration")
        print("10. Create GitHub Repository")
        print("11. Show Repository Status")
        print("12. Sync with Remote")
        print("13. Show Recent Logs")
        print("14. Resolve Conflicts")
        print("15. Backup Management")
        print("16. Detailed Status")
        print("17. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == "1":
            track_files()
        elif choice == "2":
            show_tracked_files()
        elif choice == "3":
            remove_from_tracking()
        elif choice == "4":
            show_git_config()
        elif choice == "5":
            edit_git_config()
        elif choice == "6":
            edit_config()
        elif choice == "7":
            reset_config()
        elif choice == "8":
            initialize_git()
        elif choice == "9":
            remove_git_config()
        elif choice == "10":
            create_github_repo()
        elif choice == "11":
            show_repo_status()
        elif choice == "12":
            sync_with_remote()
        elif choice == "13":
            show_recent_logs()
        elif choice == "14":
            resolve_conflicts()
        elif choice == "15":
            backup_menu()
        elif choice == "16":
            detailed_status()
        elif choice == "17":
            print("\n\t... Exiting Git Manager ...\n")
            break
        else:
            print("\nInvalid choice. Please select a valid option.\n")

def setup_logging():
    """Configures the logging system."""
    log_file = "git_manager.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add log file to gitignore if not already there
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r") as f:
            content = f.read()
        if "git_manager.log" not in content:
            with open(".gitignore", "a") as f:
                f.write("\n# Git Manager logs\ngit_manager.log\n")
    else:
        with open(".gitignore", "w") as f:
            f.write("# Git Manager logs\ngit_manager.log\n")

def log_operation(operation, status, message=""):
    """Logs an operation and its outcome."""
    level = logging.INFO if status == "SUCCESS" else logging.ERROR
    log_msg = f"{operation}: {status}"
    if message:
        log_msg += f" - {message}"
    logging.log(level, log_msg)

def show_recent_logs():
    """Displays recent log entries to the user."""
    if not os.path.exists("git_manager.log"):
        print("\nNo logs available yet.")
        return
        
    print("\nRecent Operations:")
    has_errors = False
    with open("git_manager.log", "r") as f:
        # Get last 10 lines
        lines = f.readlines()[-10:]
        for line in lines:
            parts = line.split(" - ", 2)
            if len(parts) >= 3:
                timestamp = parts[0]
                level = parts[1]
                message = parts[2].strip()
                if "ERROR" in level:
                    has_errors = True
                print(f"{timestamp} | {level} | {message}")
    
    if has_errors:
        print("\nNote: There are errors in the log that may need attention.")
    print()

def detailed_status():
    """Provides detailed repository status with actionable insights."""
    start_time = time.time()
    
    print("\nRepository Health Check")
    print("======================")
    
    # Local changes
    local_changes = subprocess.run(
        "git status --porcelain",
        shell=True, capture_output=True, text=True
    ).stdout
    
    if local_changes:
        print("\nLocal Changes:")
        for line in local_changes.splitlines():
            status, file = line[:2], line[3:]
            if status == "M ":
                print(f"Modified: {file}")
            elif status == "A ":
                print(f"Added: {file}")
            elif status == "D ":
                print(f"Deleted: {file}")
    else:
        print("\nWorking directory clean")
    
    # Remote status
    try:
        subprocess.run("git fetch", shell=True, capture_output=True)
        ahead = subprocess.run(
            "git rev-list HEAD..origin/main --count",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        behind = subprocess.run(
            "git rev-list origin/main..HEAD --count",
            shell=True, capture_output=True, text=True
        ).stdout.strip()
        
        print("\nRemote Status:")
        if ahead != "0":
            print(f"- {ahead} commits ahead of remote")
        if behind != "0":
            print(f"- {behind} commits behind remote")
        if ahead == "0" and behind == "0":
            print("- In sync with remote")
    except:
        print("- Unable to check remote status")
    
    duration = time.time() - start_time
    log_operation("Status", "INFO", f"Status check completed in {duration:.2f} seconds")

def resolve_conflicts():
    """Interactive conflict resolution helper."""
    # Check for conflicts
    status = subprocess.run(
        "git status",
        shell=True,
        capture_output=True,
        text=True
    ).stdout
    
    if "You have unmerged paths" not in status:
        print("\nNo conflicts detected")
        log_operation("Conflicts", "INFO", "No conflicts found")
        return
        
    print("\nConflict Resolution Helper")
    print("==========================")
    log_operation("Conflicts", "INFO", "Starting conflict resolution")
    
    # Get conflicted files
    conflicts = subprocess.run(
        "git diff --name-only --diff-filter=U",
        shell=True,
        capture_output=True,
        text=True
    ).stdout.split()
    
    resolved_files = []
    for file in conflicts:
        print(f"\nResolving conflicts in {file}")
        print("Options:")
        print("1. Keep local version")
        print("2. Keep remote version")
        print("3. Show diff")
        print("4. Edit manually")
        print("5. Skip file")
        
        while True:
            choice = input("\nSelect option: ")
            
            try:
                if choice == "1":
                    subprocess.run(f"git checkout --ours {file}", shell=True, check=True)
                    subprocess.run(f"git add {file}", shell=True, check=True)
                    resolved_files.append(file)
                    log_operation("Conflicts", "SUCCESS", f"Kept local version of {file}")
                    break
                    
                elif choice == "2":
                    subprocess.run(f"git checkout --theirs {file}", shell=True, check=True)
                    subprocess.run(f"git add {file}", shell=True, check=True)
                    resolved_files.append(file)
                    log_operation("Conflicts", "SUCCESS", f"Kept remote version of {file}")
                    break
                    
                elif choice == "3":
                    # Show colored diff
                    subprocess.run(f"git diff --color {file}", shell=True)
                    continue
                    
                elif choice == "4":
                    print(f"\nPlease edit {file} manually.")
                    print("After editing, mark as resolved? (y/n): ")
                    if input().lower() == 'y':
                        subprocess.run(f"git add {file}", shell=True, check=True)
                        resolved_files.append(file)
                        log_operation("Conflicts", "SUCCESS", f"Manually resolved {file}")
                        break
                    
                elif choice == "5":
                    log_operation("Conflicts", "INFO", f"Skipped {file}")
                    break
                    
                else:
                    print("Invalid choice")
                    
            except subprocess.CalledProcessError as e:
                print(f"\nError resolving conflict: {str(e)}")
                log_operation("Conflicts", "ERROR", f"Failed to resolve {file}: {str(e)}")
    
    if resolved_files:
        try:
            # Commit resolved conflicts
            commit_msg = "Resolved conflicts in: " + ", ".join(resolved_files)
            subprocess.run(
                f'git commit -m "{commit_msg}"',
                shell=True,
                check=True
            )
            print("\nConflicts resolved and committed successfully")
            log_operation("Conflicts", "SUCCESS", f"Committed resolutions for {len(resolved_files)} files")
        except subprocess.CalledProcessError as e:
            print(f"\nError committing resolved conflicts: {str(e)}")
            log_operation("Conflicts", "ERROR", f"Failed to commit resolutions: {str(e)}")
    else:
        print("\nNo conflicts were resolved")
        log_operation("Conflicts", "WARNING", "No conflicts resolved")

def backup_menu():
    """Displays backup management options."""
    while True:
        print("\nBackup Management:")
        print("1. Create backup")
        print("2. List backups")
        print("3. Restore backup")
        print("4. Return to main menu")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            backup_name = BACKUP_MANAGER.create_backup()
            print(f"\nBackup created: {backup_name}")
            log_operation("Backup", "SUCCESS", f"Created backup {backup_name}")
            
        elif choice == "2":
            backups = BACKUP_MANAGER.list_backups()
            if not backups:
                print("\nNo backups found")
            else:
                print("\nAvailable backups:")
                for timestamp, files in backups.items():
                    print(f"\n{timestamp}:")
                    for file in files:
                        print(f"  - {file}")
                        
        elif choice == "3":
            backups = BACKUP_MANAGER.list_backups()
            if not backups:
                print("\nNo backups available to restore")
                continue
                
            print("\nAvailable backups:")
            timestamps = list(backups.keys())
            for i, timestamp in enumerate(timestamps, 1):
                print(f"{i}. {timestamp}")
                
            try:
                idx = int(input("\nSelect backup to restore (or 0 to cancel): ")) - 1
                if idx == -1:
                    continue
                if 0 <= idx < len(timestamps):
                    BACKUP_MANAGER.restore_backup(timestamps[idx])
                    print("\nBackup restored successfully")
                    log_operation("Backup", "SUCCESS", f"Restored backup {timestamps[idx]}")
                else:
                    print("\nInvalid selection")
            except ValueError:
                print("\nInvalid input")
                
        elif choice == "4":
            break

def verify_tracked_file(file_name):
    """Verifies that a file is actually being tracked."""
    config = load_config()
    if config["tracked_files"] == "all":
        return True
    return file_name in config["tracked_files"]

if __name__ == "__main__":
    menu()