"""
Coordinate Finder Utility

This script is a simple helper tool to determine the coordinates of a rectangular
region on the screen. It prompts the user to position their mouse at the top-left
and bottom-right corners of the desired area and then calculates the region's
position and size.

The output is a tuple in the format (left, top, width, height), which is exactly
what the `region` parameter in the `DevysAutomation` module functions requires.

How to Use:
1.  Run the script from your terminal:
    python find_coord.py

2.  Follow the on-screen instructions:
    -   First, move your mouse to the top-left corner of the desired region.
    -   Wait for 5 seconds.
    -   Next, move your mouse to the bottom-right corner of the region.
    -   Wait for another 5 seconds.

3.  The script will print the final `(left, top, width, height)` tuple.

4.  Copy this tuple and paste it as the `search_region` value in your main
    automation script (e.g., `AutoWork.py`).
"""
import pyautogui
import time

print("This script helps you find the coordinates for a screen region.")
print("="*60)

# --- Step 1: Get the top-left corner of the desired region ---
print("\nMove your mouse to the TOP-LEFT corner of the region you want to capture.")
print("You have 5 seconds...")
time.sleep(5) # Give the user time to position the mouse. 
left, top = pyautogui.position() # Get the current (x, y) coordinates of the mouse. 
print(f"✅ Top-Left corner captured: (left={left}, top={top})")

# --- Step 2: Get the bottom-right corner of the desired region ---
print("\nNow, move your mouse to the BOTTOM-RIGHT corner of that same region.")
print("You have 5 seconds...")
time.sleep(5) # Give the user time to position the mouse. 
right, bottom = pyautogui.position() # Get the new mouse coordinates. 
print(f"✅ Bottom-Right corner captured: (right={right}, bottom={bottom})")

# --- Step 3: Calculate the width and height of the region ---
width = right - left
height = bottom - top

# --- Step 4: Display the final result in the required format ---
print("\n🎉 Success! Here are your coordinates:")
print(f"Your region is: ({left}, {top}, {width}, {height})")
print("="*60)
print("Copy this tuple and paste it into your main script as the 'search_region' value.")
