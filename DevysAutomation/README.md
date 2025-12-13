# Devy's Multi-Rule Automation Engine

A robust, GUI-based automation tool designed to create complex logic chains for games and applications without writing code.

This application allows you to capture "ingredients" (screen coordinates or images) and assign specific actions (clicks, key presses, text input) to them using a modern visual interface.

## ⚡ Key Features

* **Modern Dark UI:** Built with `customtkinter` for a clean, user-friendly experience.
* **Dual Detection Modes:**
    * **Pixel Detection:** Monitors specific coordinates for exact color changes (RGB).
    * **Image Detection:** Scans the screen for specific images/icons using OpenCV.
* **Visual Logic Builder:** Create automation rules by linking detectors to actions.
* **Action Support:**
    * Auto-Click (at found location or custom coordinates).
    * Keyboard Input (Press single keys or type text).
    * Wait/Sleep delays.
* **JSON Profile System:** Save your "detectors" as distinct `.json` files to reuse across different logic chains.
* **Live Overlay:** Includes a built-in snipping tool to capture screen regions or pick pixel colors directly.

---

## 🛠️ Installation

1.  **Clone or Download** this repository.
2.  **Install Dependencies** using `pip`. The application relies on several libraries for GUI, screen capture, and input simulation.

    ```bash
    pip install -r requirements.txt
    ```

    *Recommended `requirements.txt` content:*
    ```text
    customtkinter
    Pillow
    mss
    opencv-python
    numpy
    keyboard
    pydirectinput
    ```

3.  **Run the Application:**
    ```bash
    python StellarGames.py
    ```

---

## 📖 Usage Guide

The application is divided into two main steps: **Capturing Ingredients** and **Building Logic**.

### Step 1: Capture Ingredients (Tab 1)
This tab is where you define *what* the bot should look for.

1.  **Choose a Method:**
    * **Pixel Detect:** Click "Pick Pixel" to launch an overlay. Click anywhere on your screen to grab the X, Y, and RGB values automatically.
    * **Image Detect:** Click "Capture Region" to launch an overlay. Click and drag to draw a box around the icon, button, or enemy you want to detect.
2.  **Name & Save:** Give your detector a unique name (e.g., `accept_button` or `health_bar_low`) and click **SAVE DETECTOR**. This creates a `.json` file in your folder.

### Step 2: Build Logic Chain (Tab 2)
This tab is where you tell the bot *what to do* when it finds your ingredients.

1.  **Add Rules:** Select a saved profile from the dropdown and click **+ Add Detection Rule**. It will appear in your "Active Rules" list on the left.
2.  **Edit Actions:** Click on a rule in the list to select it. On the right side, you can now add actions to execute when that rule is triggered:
    * **Press Key:** Simulates a key press (e.g., `F`, `Enter`).
    * **Type Text:** Types a full string.
    * **Click Found Spot:** Clicks exactly where the image/pixel was detected.
    * **Click Custom (X,Y):** Clicks a specific coordinate you provide.
    * **Wait (ms):** Pauses execution (useful for preventing spam-clicking).
3.  **Prioritize:** Use the **↑** and **↓** arrows to change the order of actions.

### Step 3: Start
Click **START ALL** to begin the automation loop.
* The bot will continuously scan the screen for your active rules.
* If a rule matches, it executes the assigned action chain.
* Click **STOP** to end the process.

---

## 📂 Project Structure

* `StellarGames.py`: The main application source code.
* `images/`: Automatically created folder where captured image templates are stored.
* `*.json`: Saved detector profiles created by the user.

## ⚠️ Note on Games
This tool uses `pydirectinput` for mouse/keyboard control, which is specifically designed to work with DirectX games that often block standard Python input commands. Ensure you run this script as **Administrator** if the game requires high-level privileges.