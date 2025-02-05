# Rush-Royale-Bot
Python-based bot for Rush Royale  
Originally by @AxelBjork  
[Original Repo](https://github.com/AxelBjork/Rush-Royale-Bot)

🔹 **Use with Bluestacks on PC**  

---

## 🚀 Farm Unlimited Gold!
✅ Runs **24/7**, allowing you to **easily upgrade all available units** with gold to spare.  
✅ Optimized to farm **Dungeon Floor 5**.  

---

## ⚙️ Functionality  
🔹 Sends **low-latency** commands to the game via **Scrcpy ADB**.  
🔹 Jupyter Notebook interface for interacting and adding new units.  
🔹 **Automated tasks**: Refresh store, watch ads, complete quests, collect ad chest.  
🔹 **Unit type detection** with **OpenCV (ORB detector)**.  
🔹 **Rank detection** using **sklearn LogisticRegression** (high accuracy).  

![Output](https://user-images.githubusercontent.com/71280183/171181226-d680e7ca-729f-4c3d-8fc6-573736371dfb.png)  

![New GUI](https://user-images.githubusercontent.com/71280183/183141310-841b100a-2ddb-4f59-a6d9-4c7789ba72db.png)  

---

## 🛠 Setup Guide  

### 1️⃣ Install Python  
📥 Download and install the latest **Python 3.9 (Windows 64-bit)**:  
👉 [Python 3.9.13 Windows Installer](https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe)  

🔹 Select **"Add Python to PATH"** during installation.  
🔹 Verify installation by running:  

```sh
python --version
```

### 2️⃣ Install Bluestacks  
📥 Download and install the latest **Bluestacks 5**.  
🔹 Adjust settings:
   - **Display**: Resolution - `1600 x 900`
   - **Graphics**: Graphics engine mode - `Compatibility` (helps if you experience issues with Scrcpy)
   - **Advanced**: Enable **Android Debug Bridge (ADB)** and note the port number.  
🔹 Set up a Google account, download **Rush Royale**, and complete the initial setup.

### 3️⃣ Running the Bot  
🔹 Run the installation script to set up dependencies:  

```sh
install.bat
```

🔹 Launch the bot GUI:  

```sh
launch_gui.bat
```

🔹 *(Temporary step)* Configure units and settings in `bot_handler.py`. This will later be moved to `config.ini`.

🎉 **You're all set!** The bot should now be ready to use.
