# Rush-Royale-Bot
 **CURRENTLY NOT WORKING! I AM WORKING ON A PATCH TO FIX IT!** (07.04.2025)
Python based bot for Rush Royale

Use with Bluestacks on PC

## Farm unlimited gold!
* Can run 24/7 and allow you to easily upgrade all available units with gold to spare.
* Optimized to farm dungeon floor 5

## Functionality
* Can send low latency commands to game via Scrpy ADB
* Jupyter notebook for interacting, adding new units
* Automatically refreshes store, watches ads, completes quests, collects ad chest
* Unit type detection with openCV: ORB detector
* Rank detection with sklearn LogisticRegression (Very accurate)

![output](https://user-images.githubusercontent.com/71280183/171181226-d680e7ca-729f-4c3d-8fc6-573736371dfb.png)

![new_gui](https://user-images.githubusercontent.com/71280183/183141310-841b100a-2ddb-4f59-a6d9-4c7789ba72db.png)

## Planned Features

* **Improved Dungeon Selection:** Ability to select different dungeon floors and customize farming strategies.
* **Talent Selection:** Automatically select and upgrade unit talents based on configurations.
* **Clan Features:** Automatically accept clan members (optional), participate in clan gifts.
* **Event Support:** Automatically play events and collect rewards.
* **Intelligent Deck Adjustment:** Suggestions for deck improvements based on collected units and runes.
* **Visual Debugging Tools:** Integration of visualizations for better monitoring of bot behavior.
* **Extended Configuration Options:** More detailed settings for farming strategies, unit detection, and other functions via a configuration file or GUI.
* **Support for More Emulators:** Expanding compatibility to other Android emulators besides Bluestacks.
* **Error Handling and Reporting:** Improved error detection and more detailed logging of bot operation.
* **GUI Improvements:** More user-friendly interface for bot configuration and control.

## Setup Guide

**Python**

Install Latest Python 3.9 (Windows installer 64-bit)

[https://www.python.org/downloads/](https://www.python.org/downloads/) (windows 64-bit installer) [[https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe](https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe)]

Select add Python to path, check `python --version` works and gives Python 3.9.13

Download and extract this repo

**Bluestacks**

Install Latest Bluestacks 5

Settings:

(Display) Resolution: 1600 x 900

(Graphics) Graphics engine mode: Compatibility (this can help if you have issues with scrcpy)

(Advanced) Android Debug Bridge: Enabled - Note the port number here

Setup google account, download rush royale, ect.

**Bot**

run `install.bat` to create repo and install dependencies

run `launch_gui.bat`

(temp) units and other settings have to be configured in `bot_handler.py`, this will be moved to the `config.ini` file.
