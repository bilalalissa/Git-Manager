import os
from datetime import datetime
from cryptography.fernet import Fernet
import json
import shutil

class BackupManager:
    def __init__(self, config_file, key_file):
        self.config_file = config_file
        self.key_file = key_file
        self.backup_dir = "backups"
        
    def create_backup(self):
        """Creates a backup of current configuration and key."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_base = f"backup_{timestamp}"
        
        # Backup config file
        if os.path.exists(self.config_file):
            config_backup = os.path.join(self.backup_dir, f"{backup_base}_config.json")
            shutil.copy2(self.config_file, config_backup)
            
        # Backup key file
        if os.path.exists(self.key_file):
            key_backup = os.path.join(self.backup_dir, f"{backup_base}_key.enc")
            shutil.copy2(self.key_file, key_backup)
            
        return backup_base
    
    def list_backups(self):
        """Lists available backups."""
        if not os.path.exists(self.backup_dir):
            return []
            
        backups = {}
        for file in os.listdir(self.backup_dir):
            if file.startswith("backup_"):
                timestamp = file.split("_")[1]
                if timestamp not in backups:
                    backups[timestamp] = []
                backups[timestamp].append(file)
                
        return backups
    
    def restore_backup(self, timestamp):
        """Restores configuration from a backup."""
        backup_base = f"backup_{timestamp}"
        config_backup = os.path.join(self.backup_dir, f"{backup_base}_config.json")
        key_backup = os.path.join(self.backup_dir, f"{backup_base}_key.enc")
        
        if os.path.exists(config_backup):
            shutil.copy2(config_backup, self.config_file)
        if os.path.exists(key_backup):
            shutil.copy2(key_backup, self.key_file) 