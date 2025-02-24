import os
import json
import subprocess
import time
import base64
import sys
from cryptography.fernet import Fernet
import platform
import requests

CONFIG_FILE = "tracked_files.json"
ENCRYPTION_KEY_FILE = "encryption.key"
SERVICE_FILE = "/etc/systemd/system/git-tracker.service" if platform.system() == "Linux" else "git-tracker.bat"
GITHUB_API_URL = "https://api.github.com/user/repos"

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
    default_config = {
        "repo_url": "",
        "tracked_files": [],
        "auto_commit": False,
        "daemon_mode": False,
        "commit_interval": 30,
        "github_token": "",
        "last_commit_time": None,
        "remote_branch": "main"
    }
    
    # If file doesn't exist, return defaults
    if not os.path.exists(CONFIG_FILE):
        return default_config

    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Simple file read operation
            with open(CONFIG_FILE, "r", encoding='utf-8') as file:
                data = file.read().strip()
                
            # If file is empty, return defaults
            if not data:
                return default_config
                
            # Try to decrypt and parse the data
            config = decrypt_data(data)
            # Ensure all expected keys exist
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
            
        except (IOError, OSError) as e:
            if attempt < max_retries - 1:
                print(f"\nRetrying file read... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            print(f"\nError reading configuration file: {str(e)}")
            return default_config
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            return default_config

def save_config(config):
    """Encrypts and saves configuration securely."""
    try:
        # Encrypt the configuration
        encrypted_data = encrypt_data(config)
        
        # Simple direct write
        with open(CONFIG_FILE, "w", encoding='utf-8') as file:
            file.write(encrypted_data)
            
        return True
    except Exception as e:
        print(f"\nError saving configuration: {str(e)}")
        return False

def reset_config():
    """Resets Git Manager configuration to defaults."""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
    print("\n\t== >Git Manager configuration has been reset.\n")

def track_files():
    """Allows user to add files to Git tracking."""
    config = load_config()
    files_added = False
    
    while True:
        file_name = input("\nEnter file to track \n(or type 'all' to track all files, 'done' to finish): ")
        if file_name.lower() == "done":
            break
        elif file_name.lower() == "all":
            try:
                result = subprocess.run("git add .", shell=True, check=True, capture_output=True, text=True)
                if result.returncode == 0:
                    config["tracked_files"] = "all"
                    files_added = True
                    print("\nAll files have been staged for tracking")
                break
            except subprocess.CalledProcessError as e:
                print(f"\nError adding files: {e.stderr}")
        elif os.path.exists(file_name):
            try:
                result = subprocess.run(f"git add {file_name}", shell=True, check=True, capture_output=True, text=True)
                if result.returncode == 0:
                    config["tracked_files"].append(file_name)
                    files_added = True
                    print(f"\nAdded {file_name} to tracking")
            except subprocess.CalledProcessError as e:
                print(f"\nError adding {file_name}: {e.stderr}")
        else:
            print("\nFile not found.\n")
    
    if files_added:
        save_config(config)
        # Commit the changes
        try:
            subprocess.run('git commit -m "Added new files to tracking"', shell=True, check=True)
            print("\nChanges committed successfully")
        except subprocess.CalledProcessError as e:
            print(f"\nError committing changes: {e.stderr}")

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
            else:  # If disabling auto-commit
                if save_config(config):
                    print("\nAuto-Commit disabled")
                else:
                    # Revert changes if save failed
                    config["auto_commit"] = True
                    print("\nFailed to save configuration")
            
        elif choice == "2":
            old_value = config["daemon_mode"]
            config["daemon_mode"] = not config["daemon_mode"]
            if save_config(config):
                print(f"\nDaemon Mode {'Enabled' if config['daemon_mode'] else 'Disabled'}")
            else:
                # Revert changes if save failed
                config["daemon_mode"] = old_value
                print("\nFailed to save configuration")
            
        elif choice == "3" and config["auto_commit"]:
            old_interval = config["commit_interval"]
            interval = input("\nEnter new commit interval in minutes: ")
            try:
                config["commit_interval"] = int(interval)
                if save_config(config):
                    print(f"\nCommit interval updated to {interval} minutes")
                else:
                    # Revert changes if save failed
                    config["commit_interval"] = old_interval
                    print("\nFailed to save configuration")
            except ValueError:
                print("\nInvalid interval. Keeping current setting.")
        else:
            print("\nInvalid choice.")
            return
            
    except Exception as e:
        print(f"\nError updating configuration: {str(e)}")

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
    while True:
        file_name = input("\nEnter file to remove from tracking (or type 'done' to finish): ")
        if file_name.lower() == "done":
            break
        subprocess.run(f"git rm --cached {file_name}", shell=True)
        print(f" - Removed {file_name} from tracking.")
    subprocess.run("git commit -m 'Removed files from tracking'", shell=True)
    subprocess.run("git push origin main", shell=True)

def remove_git_config():
    """Removes Git configuration and all related files."""
    confirm = input("\nAre you sure you want to remove the Git configuration? (y/n): ")
    if confirm.lower() == "y":
        try:
            # Remove Git directory
            if os.path.exists(".git"):
                subprocess.run("rm -rf .git", shell=True)
                print("- Git repository removed")

            # Remove configuration files
            files_to_remove = [
                CONFIG_FILE,                  # tracked_files.json
                ENCRYPTION_KEY_FILE,          # encryption.key
                f"{CONFIG_FILE}.backup",      # tracked_files.json.backup
            ]
            
            for file in files_to_remove:
                if os.path.exists(file):
                    os.remove(file)
                    print(f"- Removed {file}")

            print("\nGit configuration and related files have been removed.\n")
            print("You can initialize a new repository using option 8 or")
            print("create a new GitHub repository using option 10.\n")
            
        except Exception as e:
            print(f"\nError removing files: {str(e)}\n")
    else:
        print("\nRemoval cancelled.\n")

def create_github_repo():
    """Creates a new repository on GitHub and configures it locally."""
    try:
        print("\n=== GitHub Repository Setup ===")
        
        # Get GitHub token
        config = load_config()
        github_token = config.get("github_token")
        if not github_token:
            github_token = input("\nEnter your GitHub personal access token: ").strip()
            if not github_token:
                print("\nNo GitHub token provided. Cannot proceed with setup.\n")
                return
            config["github_token"] = github_token
            save_config(config)

        # Verify GitHub token
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        username_response = requests.get("https://api.github.com/user", headers=headers)
        if username_response.status_code != 200:
            print("\nInvalid GitHub token. Please check your credentials.\n")
            return
        
        username = username_response.json().get("login")
        print(f"\nAuthenticated as: {username}")

        # Get repository details
        print("\n=== Repository Details ===")
        repo_name = input("Enter repository name: ").strip()
        if not repo_name:
            print("\nRepository name is required.\n")
            return

        description = input("Enter repository description (optional): ").strip()
        private = input("Make repository private? (y/n): ").strip().lower() == 'y'

        # Create GitHub repository
        data = {
            "name": repo_name,
            "description": description,
            "private": private
        }
        create_response = requests.post(GITHUB_API_URL, json=data, headers=headers)
        
        if create_response.status_code != 201:
            print(f"\nError creating repository: {create_response.json().get('message')}")
            return

        # Repository created successfully
        repo_url = f"https://github.com/{username}/{repo_name}.git"
        print("\n=== Repository Created Successfully ===")
        print(f"- URL: {repo_url}")
        print(f"- Visibility: {'Private' if private else 'Public'}")
        
        # Ask to initialize locally
        init_local = input("\nDo you want to initialize this repository locally? (y/n): ")
        if init_local.lower() == "y":
            if not os.path.exists(".git"):
                subprocess.run("git init", shell=True, check=True)
                subprocess.run("git branch -M main", shell=True, check=True)
            
            remote_url = f"https://{github_token}@github.com/{username}/{repo_name}.git"
            subprocess.run(f"git remote add origin {remote_url}", shell=True, check=True)
            
            config["repo_url"] = repo_url  # Save the clean URL
            save_config(config)
            print("\nLocal repository initialized and configured.\n")
        else:
            print("\nRemote repository created. You can clone it later using:")
            print(f"git clone {repo_url}\n")

    except Exception as e:
        print(f"\nError: {str(e)}\n")

def show_tracking_files():
    """Displays the list of tracked files."""
    tracked_files = subprocess.run("git ls-files", shell=True, capture_output=True, text=True).stdout.strip()
    print("\nTracked Files:")
    print(tracked_files if tracked_files else "No tracked files found.\n")

def show_repo_status():
    """Displays the current Git repository status."""
    repo_status = subprocess.run("git status", shell=True, capture_output=True, text=True).stdout.strip()
    print("\nRepository Status:")
    print(repo_status)
    print("\n")

def auto_commit_process():
    """Handles automatic commits and pushes for tracked files only"""
    print("\nAuto-commit process started...")
    error_count = 0  # Track consecutive errors
    
    while True:
        try:
            config = load_config()
            if not config["auto_commit"]:
                print("\nAuto-commit disabled.")
                return  # Exit the thread when auto-commit is disabled
                
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
                    # Stage changes first
                    if tracked_files == "all":
                        subprocess.run("git add .", shell=True, check=True, timeout=30)
                    else:
                        for file in tracked_files:
                            if os.path.exists(file):
                                subprocess.run(
                                    f"git add {file}",
                                    shell=True,
                                    check=True,
                                    timeout=30
                                )
                    
                    # Commit changes
                    subprocess.run(
                        'git commit -m "Auto-commit: Changes in tracked files"',
                        shell=True,
                        check=True,
                        timeout=30
                    )
                    
                    # Try to push directly first
                    try:
                        subprocess.run(
                            "git push origin main",
                            shell=True,
                            check=True,
                            timeout=30
                        )
                    except subprocess.CalledProcessError:
                        # If push fails, try pull with allow-unrelated-histories
                        subprocess.run(
                            "git pull origin main --allow-unrelated-histories",
                            shell=True,
                            check=True,
                            timeout=30
                        )
                        # Try push again
                        subprocess.run(
                            "git push origin main",
                            shell=True,
                            check=True,
                            timeout=30
                        )
                    
                    print("\nChanges committed and pushed successfully")
                    error_count = 0  # Reset error count on success
                    
                except subprocess.TimeoutExpired:
                    error_count += 1
                    if error_count >= 3:
                        print("\nAuto-commit stopped due to timeouts.")
                        return
                    continue
                    
                except subprocess.CalledProcessError:
                    error_count += 1
                    if error_count >= 3:
                        print("\nAuto-commit stopped due to errors.")
                        return
                    continue
            
            # Wait for next check
            interval = config.get("commit_interval", 30)
            time.sleep(interval * 60)
            
        except Exception:
            error_count += 1
            if error_count >= 3:
                print("\nAuto-commit stopped due to repeated errors.")
                return
            time.sleep(300)  # Wait 5 minutes before retry

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
    generate_key()
    verify_config_files()
    show_welcome = True
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Verify repository status
    repo_valid, repo_message = verify_git_repo()
    if not repo_valid:
        print(f"\nWarning: {repo_message}")
        print("Use option 8 to initialize repository if needed.\n")
    
    # Start auto-commit in a separate thread if enabled
    config = load_config()
    if config["auto_commit"]:
        import threading
        auto_commit_thread = threading.Thread(target=auto_commit_process, daemon=True)
        auto_commit_thread.start()
    
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
        print("13. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == "1":
            track_files()
        elif choice == "2":
            show_tracking_files()
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
            print("\n\t... Exiting Git Manager ...\n")
            break
        else:
            print("\nInvalid choice. Please select a valid option.\n")

if __name__ == "__main__":
    menu()