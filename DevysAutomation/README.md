# 🌌 Stellar Automation Engine Pro

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)](https://python.org)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-darkgreen)](https://github.com/tomschimansky/CustomTkinter)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)](https://microsoft.com)

An elite, high-performance, and visually stunning visual macro automation engine. Designed specifically for advanced game scripting and application workflows, **Stellar Automation Engine Pro** allows you to construct robust, non-linear logic chains using precise pixel checking, optimized image detection, HSV color ranges, and OCR text matching without writing a single line of code.

Featuring a **Live Macro Recorder & Visual Timeline Editor**, **HSV Color Range Gradients**, **OCR Text Recognition**, a **Finite State Machine (FSM) Logic Controller**, **Humanize Mode (Anti-Cheat Bypass)**, a **15x Optimized Template Scanner**, and **Interactive Neon Diagnostics overlays**, it provides desktop automation capabilities with a professional gamer aesthetic.

---

## ⚡ Core Technical Features

### 🎙️ Live Macro Recording Hook
Ditch manual coordinate typing and keyboard entry. Record your real actions live inside games or desktop applications:
* **Background Hooking:** Track global keyboard keystrokes and mouse clicks in real-time, even when clicked into third-party game clients.
* **Smart Translators:** Automatically converts performance sessions into distinct, editable visual timeline steps.
* **Automatic Delays:** Captures authentic elapsed timing between clicks/keys and auto-fills wait buffers.
* **Hotkey Controls:** Toggle recording instantly from anywhere on your desktop by pressing the **F10** key.

### 📊 Visual Timeline Editor & Drag-and-Drop Reordering
Constructing and optimizing sequences is highly interactive inside our custom-styled vertical timeline:
* **Interactive Drag-and-Drop Reordering:** Simply grab any sequence card or delay pill by its tactile handle (`⠿`) and drag it up or down to reorder steps in real-time. Cards smoothly shuffle on-screen with instant visual feedback and update the logic model dynamically.
* **Smart Edge Auto-Scroll:** Dragging a step near the top or bottom edges of the sequence viewport automatically scrolls the list, allowing seamless reordering of large automation chains.
* **Color-Coded Nodes:** Connects sequence steps using vertical timeline guides and action icons, color-coded by action category (e.g., Cyan for keys, Neon Green for mouse clicks, Purple for FSM state switches, Grey for delays).
* **Inline Delay Pills:** Sequence delays are styled as sleek, dark delay pills.
* **Tactile Micro-Adjustments:** Dial in timing without typing! Add or subtract wait times instantly using the inline **`-50ms`** and **`+50ms`** buttons directly inside the timeline pill.

### 🌈 HSV Color Range Gradient Detector
Many game interfaces use color gradients (such as shifting red health bars or mana pools) that break standard single-pixel coordinate rules.
* **Region-Based Gradients:** Captures a coordinate region and isolates specific ranges in Hue, Saturation, Value (HSV) color spaces.
* **Match Ratio Threshold:** Calculates the precise percentage of pixels in the region matching the color range ($1\% - 100\%$) to trigger action sequences.
* **Built-in Presets:** Includes dynamic pre-loaded ranges for **Red Health**, **Green Health**, **Blue Mana**, **Yellow Quest Markers**, and **Orange Active Elements** that automatically populate threshold fields.

### ✍️ OCR Text Recognition (Optical Character Recognition)
Automate interfaces based on live on-screen text events, such as waiting for cooldown labels, matching lobby messages, or detecting text cues (e.g., "Victory" or "Defeat"):
* **Targeted Extraction:** Scans customized regional viewports for text blocks using PyTesseract.
* **Flexible Comparison Modes:**
  * **Contains:** Triggers if the target phrase appears anywhere in the captured text.
  * **Exact Match:** Triggers only if the text matches exactly.
  * **Regex:** Leverages complete Regular Expression patterns.
* **Live In-Editor Modifications:** Update target search phrases directly within the Sequencing tab without re-recording profiles.

### ⚙️ Finite State Machine (FSM) & Loop Controls
Stellar integrates a powerful FSM engine that lets you build stateful, branch-dependent macro environments:
* **Trigger Preconditions:** Rules can define mandatory variable comparisons (e.g., only trigger Rule B if state variable `phase` `==` `boss_fight`).
* **State Modification Actions:** Trigger sequence state changes when a rule matches.
* **Mathematical Counters:** State setter actions support incremental and decremental operations (e.g., modifying `loop_count` by `+1` or `-1`) for loops and escape parameters.

### 🛡️ Humanize Mode (Heuristic Anti-Cheat Bypass)
Bot detection algorithms scan for instantaneous, perfectly repeated computer inputs. The built-in **Humanize** layer randomizes interactions to mimic an organic human operator:
* **Organic Clicking:** Randomized click coordinates (±4px offset) paired with authentic click-hold timings ($55\text{ms} - 125\text{ms}$).
* **Dynamic Typing Cadence:** Character-by-character string writing with simulated finger travel times ($35\text{ms} - 110\text{ms}$ per character) and random typing hesitations ($150\text{ms} - 300\text{ms}$).
* **Timing Jitter:** Sequence wait delays include a dynamic $\pm15\%$ jitter variance.
* **Hand-Tremor Dragging:** Mouse Drag & Drop executes along an organic **S-Curve (Ease-In-Ease-Out)** path using trigonometric interpolation, complete with micro-deviations mimicking physical muscle tremors.

### 🏎️ Regional Template Match (ROI Optimization)
* **Targeted Scanning:** Stellar uses a restricted **Region of Interest (ROI)** padding system: `(x1-10, y1-10, x2+10, y2+10)`.
* **15x Speedup:** By constraining OpenCV matching calculations to localized coordinates, detection routines run in **$<2\text{ms}$** with negligible CPU footprints.

### 🔍 Interactive Live Neon Diagnostics
Verify match logic instantaneously before launching automation profiles:
* **Hollow Green Bounding Boxes:** An advanced Windows graphics layer generates a transparent green box directly highlighting matched targets on your screen.
* **No-Overlap Windows:** The diagnostics viewport does not intercept mouse clicks or key inputs, allowing you to debug live environments.

---

## 📦 Complex Input Sequences Supported

* **Press Key:** Keystrokes with configurable hold durations.
* **Key Down (Hold) & Key Up (Release):** Separate events to sustain movements or drag triggers.
* **Type Text:** Natural character streams.
* **Wait (ms):** Accurate delays with humanized jitter options.
* **Click Found Spot:** Left click, Right click, or Double click exactly where the template/pixel was matched.
* **Click Custom (X, Y):** Absolute coordinates trigger paths.
* **Mouse Scroll:** Precise vertical scrolling increments.
* **Drag and Drop:** Mathematically modeled bezier-like cursor movement paths.
* **Set State Variable:** FSM state controllers supporting absolute values (e.g. `stage=boss_fight`) and math (e.g. `loops=+1`).

---

## ⚙️ Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/DevyLG/CodingChronicles.git
   cd CodingChronicles/DevysAutomation
   ```

2. **Initialize Environment & Install Dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR (Required for OCR Text Detection):**
   * Download and install the Tesseract-OCR binary on your Windows machine from the [Tesseract Repository](https://github.com/UB-Mannheim/tesseract/wiki).
   * Ensure Tesseract is added to your Windows System Path (`C:\Program Files\Tesseract-OCR` by default).

4. **Run Application:**
   ```bash
   python StellarGames.py
   ```

---

## 🏗️ Building a Standalone Distributable Binary (`.exe`)

The codebase is fully optimized for standalone deployment using PyInstaller.

To bundle the application into a single, light-weight, console-less executable on Windows:

```powershell
pip install pyinstaller
pyinstaller StellarGames.spec
```

The resulting executable will be available at:
📁 `dist/StellarGames.exe`

---

## 📂 Project Architecture

```plaintext
DevysAutomation/
├── StellarGames.py        # Complete Application Source Code
├── StellarGames.spec      # PyInstaller Packaging Configuration
├── requirements.txt       # Hardened Python Package Manifests
├── images/                # Local database for user-captured template snips
└── dist/                  # Output directory for compiled standalone binary
```

---

## 📜 License & Disclaimers

Distributed under the MIT License. See `LICENSE` for more information.

*Disclaimer: This tool is intended for educational, macro-testing, and single-player game accessibility purposes. Check game-specific End User License Agreements (EULA) before utilizing pixel macros in multiplayer environments.*