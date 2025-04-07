import os
import sys
import json
import requests
import zipfile
import shutil
from subprocess import Popen
import configparser

def check_for_updates(current_version="1.1"):
    """
    Check for updates to the Rush Royale Bot by querying GitHub releases
    Returns: (bool has_update, str latest_version, str download_url)
    """
    print("Checking for updates...")
    try:
        # Query GitHub API for latest release
        response = requests.get(
            "https://api.github.com/repos/AxelBjork/Rush-Royale-Bot/releases/latest",
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"Error checking for updates: HTTP {response.status_code}")
            return False, current_version, None
        
        data = response.json()
        latest_version = data.get('tag_name', '').replace('v', '')
        
        # Compare versions
        if latest_version and latest_version > current_version:
            download_url = None
            for asset in data.get('assets', []):
                if asset.get('name', '').endswith('.zip'):
                    download_url = asset.get('browser_download_url')
                    break
            
            if download_url:
                print(f"Update available: v{latest_version}")
                return True, latest_version, download_url
        
        print(f"No updates available. Current version: v{current_version}")
        return False, current_version, None
    
    except Exception as e:
        print(f"Error checking for updates: {str(e)}")
        return False, current_version, None

def download_update(download_url, output_file="update.zip"):
    """
    Download the update zip file
    """
    print(f"Downloading update from {download_url}...")
    try:
        response = requests.get(download_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        # Show progress bar
        block_size = 1024  # 1 Kibibyte
        progress_bar_length = 50
        
        with open(output_file, 'wb') as file:
            downloaded = 0
            for data in response.iter_content(block_size):
                file.write(data)
                downloaded += len(data)
                
                # Update progress bar
                done = int(progress_bar_length * downloaded / total_size)
                sys.stdout.write(f"\r[{'█' * done}{'.' * (progress_bar_length - done)}] {downloaded/1024/1024:.2f}/{total_size/1024/1024:.2f} MB")
                sys.stdout.flush()
        
        print("\nDownload complete!")
        return True
    except Exception as e:
        print(f"Error downloading update: {str(e)}")
        return False

def backup_config():
    """
    Backup config.ini before updating
    """
    try:
        if os.path.exists('config.ini'):
            shutil.copy('config.ini', 'config.ini.backup')
            return True
    except Exception as e:
        print(f"Error backing up config: {str(e)}")
    return False

def install_update(update_file="update.zip", backup=True):
    """
    Install the downloaded update
    """
    if backup:
        backup_config()
    
    print("Installing update...")
    try:
        # Extract zip to temp directory
        with zipfile.ZipFile(update_file, 'r') as zip_ref:
            # Get the root folder name in the zip
            root_folder = zip_ref.namelist()[0].split('/')[0] if '/' in zip_ref.namelist()[0] else ''
            
            # Extract to temp directory
            temp_dir = "update_temp"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            zip_ref.extractall(temp_dir)
            
            # If zip has a root folder, move contents from that folder
            source_dir = os.path.join(temp_dir, root_folder) if root_folder else temp_dir
            
            # Copy files (skipping config.ini)
            for item in os.listdir(source_dir):
                source_item = os.path.join(source_dir, item)
                dest_item = item
                
                # Skip config file
                if item == 'config.ini':
                    continue
                
                # Remove existing file/folder
                if os.path.exists(dest_item):
                    if os.path.isdir(dest_item):
                        shutil.rmtree(dest_item)
                    else:
                        os.remove(dest_item)
                
                # Copy new file/folder
                if os.path.isdir(source_item):
                    shutil.copytree(source_item, dest_item)
                else:
                    shutil.copy2(source_item, dest_item)
        
        # Clean up
        shutil.rmtree(temp_dir)
        os.remove(update_file)
        
        print("Update installed successfully!")
        return True
    
    except Exception as e:
        print(f"Error installing update: {str(e)}")
        return False

def restore_config():
    """
    Restore config.ini after updating
    """
    try:
        if os.path.exists('config.ini.backup'):
            # If we have a new default config, merge settings
            if os.path.exists('config.ini'):
                try:
                    # Read backup config
                    backup_config = configparser.ConfigParser()
                    backup_config.read('config.ini.backup')
                    
                    # Read new config
                    new_config = configparser.ConfigParser()
                    new_config.read('config.ini')
                    
                    # Merge settings from backup into new config
                    for section in backup_config.sections():
                        if not new_config.has_section(section):
                            new_config.add_section(section)
                        
                        for key, value in backup_config.items(section):
                            new_config.set(section, key, value)
                    
                    # Write merged config
                    with open('config.ini', 'w') as configfile:
                        new_config.write(configfile)
                    
                except Exception as e:
                    print(f"Error merging configs: {str(e)}")
                    # Fallback to just copying the backup
                    shutil.copy('config.ini.backup', 'config.ini')
            else:
                # No new config, just restore backup
                shutil.copy('config.ini.backup', 'config.ini')
            
            # Remove backup
            os.remove('config.ini.backup')
            
            print("Configuration restored successfully")
            return True
    except Exception as e:
        print(f"Error restoring config: {str(e)}")
    
    return False

def run_update():
    """
    Run the complete update process
    """
    current_version = "1.1"  # Current version
    
    has_update, latest_version, download_url = check_for_updates(current_version)
    
    if has_update and download_url:
        # Ask for confirmation
        response = input(f"Update to version {latest_version} available. Do you want to update? (y/n): ")
        
        if response.lower() == 'y':
            if download_update(download_url):
                success = install_update("update.zip")
                if success:
                    restore_config()
                    
                    print("\nUpdate complete! The bot will now restart.")
                    input("Press Enter to continue...")
                    
                    # Restart the bot
                    os.system("launch_gui.bat")
                    sys.exit(0)
    else:
        print("No updates available.")
        input("Press Enter to continue...")

if __name__ == "__main__":
    run_update()