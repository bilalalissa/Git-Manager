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

def track_files():
    """Allows user to add files to Git tracking."""
    config = load_config()
    while True:
        file_name = input("\nEnter file to track \n(or type 'all' to track all files, 'done' to finish): ")
        if file_name.lower() == "done":
            break
        elif file_name.lower() == "all":
            subprocess.run("git add .", shell=True)
            config["tracked_files"] = "all"
            break
        elif os.path.exists(file_name):
            subprocess.run(f"git add {file_name}", shell=True)
            config["tracked_files"].append(file_name)
        else:
            print("\nFile not found.\n")
    save_config(config)

def edit_config():
    """Allows user to modify the encrypted JSON configuration."""
    config = load_config()
    print("\nEdit Configuration:")
    print(f"1. Repo URL: {config['repo_url']}")
    print(f"2. Auto-Commit: {'Enabled' if config['auto_commit'] else 'Disabled'}")
    print(f"3. Daemon Mode: {'Enabled' if config['daemon_mode'] else 'Disabled'}")
    choice = input("\nEnter the number of the setting to edit (or 'q' to quit): ")
    if choice == "1":
        new_url = input("\nEnter new repository URL: ")
        config["repo_url"] = new_url
    elif choice == "2":
        config["auto_commit"] = not config["auto_commit"]
        print(f"\nAuto-Commit {'Enabled' if config['auto_commit'] else 'Disabled'}\n")
    elif choice == "3":
        config["daemon_mode"] = not config["daemon_mode"]
        print(f"\nDaemon Mode {'Enabled' if config['daemon_mode'] else 'Disabled'}\n")
    else:
        print("\nInvalid choice.")
    save_config(config)
    print("\n")

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

def initialize_git():
    """Checks if a Git configuration exists, otherwise initializes a new repository."""
    if os.path.exists(".git"):
        print("\nGit repository already initialized in this folder.\n")
    else:
        confirm = input("\n\tNo Git repository found. \nDo you want to initialize one? (y/n): ")
        if confirm.lower() == "y":
            subprocess.run("git init", shell=True)
            repo_url = input("\nEnter remote repository URL: ")
            subprocess.run(f"git remote add origin {repo_url}", shell=True)
            config = load_config()
            config["repo_url"] = repo_url
            save_config(config)
            print("\n\tGit repository initialized successfully.\n")

def remove_git_config():
    """Removes Git configuration from the folder and the application settings."""
    confirm = input("Are you sure you want to remove the Git configuration from this folder? (y/n): ")
    if confirm.lower() == "y":
        subprocess.run("rm -rf .git", shell=True)
        reset_config()
        print("\nGit configuration has been removed from the folder \nand the application.\n")

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

def menu():
    """Displays the interactive menu."""
    generate_key()
    # Define a boolean variable to show welcome message only once, when the program starts
    show_welcome = True
    # Clear the screen in macos and linux and windows
    os.system('cls' if os.name == 'nt' else 'clear')
    # If condition to show welcome message only once
    if show_welcome:
        print("\n\t==  Welcome to Git Manager  ==\n")
        show_welcome = False
        
    while True:
        print("\nGit Manager Menu:")
        print("1. Track Files")
        print("2. Show Tracked Files")
        print("3. Remove Files from Tracking")
        print("4. Show Git Configuration")
        print("5. Edit Git Configuration")
        print("6. Edit Application Settings")
        print("7. Reset Git Manager Configuration")
        print("8. Initialize Git Repository")
        print("9. Remove Git Configuration")
        print("10. Create GitHub Repository")
        print("11. Show Repository Status")
        print("12. Exit")
        
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
            print("\n\t... Exiting Git Manager ...\n")
            break
        else:
            print("\nInvalid choice. Please select a valid option.\n")

if __name__ == "__main__":
    menu()