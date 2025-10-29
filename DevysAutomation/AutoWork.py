"""
This script is an example of how to use the DevysAutomation module to automate a task.
In this case, it's designed to automate "SuperLife," a hypothetical game or application.

The script works by repeatedly taking screenshots of a specific region of the screen,
searching for predefined images within that screenshot, and then performing actions
like clicking or pressing keys based on which images are found.

How to Use:
1.  Configure the `wait_image` and `click_list` dictionaries.
    -   `path`: The filename of the image to search for (e.g., 'button.png').
    -   `threshold`: How closely the image on screen must match the template image (0.0 to 1.0).
    -   `method`: The image comparison method to use (e.g., cv2.TM_CCOEFF_NORMED).
    -   `grayscale` (optional): Set to True to search in grayscale, which can be faster.

2.  Define the `search_region`.
    -   This is CRITICAL for performance. Set the (left, top, width, height) coordinates
        to create a bounding box around the area where the script should look for images.
        Use a tool like the included `find_coord.py` to get these coordinates.

3.  Customize the `slurp_soda()` function.
    -   This function is called when the `wait_image` is found. Modify it to perform
        the specific actions you need during a "waiting" state.

4.  Run the script from your terminal:
    python AutoWork.py

5.  To stop the script, press Ctrl+C in the terminal.
"""
import DevysAutomation as GA
import cv2
import time
import pyautogui as pag
import keyboard as kb
import mss
import numpy as np


# This is an example script to automate SuperLife.




# Set to True to enable debug mode in the DevysAutomation module, which may print extra information.
DEBUG = False


# --- Configuration ---
# A list of images to search for that indicate the script should wait.
# If any of these are found, the `slurp_soda()` function is called.
# Default is color search. You can override per image with 'grayscale': True/False
wait_image = [{'path': 'cantwork.png', 'threshold': 0.90, 'method': cv2.TM_CCOEFF_NORMED}]

# A list of images to search for that should be clicked.
# The script will click the center of the first image found from this list.
click_list = [
    {'path': 'okay.png', 'threshold': 0.90, 'method': cv2.TM_CCOEFF_NORMED},
    {'path': 'work_button_hover.png', 'threshold': 0.72, 'method': cv2.TM_CCOEFF_NORMED, 'grayscale': True},
    {'path': 'work_button.png', 'threshold': 0.60, 'method': cv2.TM_CCOEFF_NORMED, 'grayscale': False},
]

# --- IMPORTANT: DEFINE A SEARCH REGION ---
# Searching a small area is much faster than the whole screen.
# Adjust these coordinates to cover all your buttons.
# Use find_coord.py to help you find the right coordinates for your screen.
search_region = (346, 420, 1181, 420) # Example: (left, top, width, height)
monitor_region = {"top": search_region[1], "left": search_region[0], "width": search_region[2], "height": search_region[3]}

def slurp_soda():
    """
    A custom function to be called when a "wait" condition is met.
    In this example, it simulates pressing keys and clicking to "slurp soda".
    """
    kb.press_and_release('3')
    time.sleep(0.25)
    pag.click(646, 456)
    kb.press_and_release('3')
    time.sleep(0.1)
    kb.press_and_release('e')

print("Starting automation. Press Ctrl+C to stop.")

# --- Main Loop (Optimized) ---
# This loop is optimized to only capture the screen once per iteration.
with mss.mss() as sct:
    while True:
        # 1. Take ONE screenshot of the defined region.
        screen_capture_img = sct.grab(monitor_region)
        # Convert the screenshot to a format OpenCV can work with.
        screen_capture = cv2.cvtColor(np.array(screen_capture_img), cv2.COLOR_BGRA2BGR)

        # 2. Search for the "wait" image in the captured screenshot.
        is_waiting = GA.locate(
            image_configs=wait_image,
            screen_capture=screen_capture
        )

        # If a "wait" image is found, perform the wait action and restart the loop.
        if is_waiting is not None:
            slurp_soda()
            continue # Skip the rest of the loop and start a new iteration.

        # 3. If not in a "wait" state, search for "click" images in the SAME screenshot.
        found_work = GA.locate(
            image_configs=click_list,
            screen_capture=screen_capture # Reuse the same screenshot for efficiency.
        )
        
        # If a "click" image is found, click it.
        if found_work is not None:
            # Calculate the absolute screen coordinates to click.
            # The coordinates from locate() are relative to the search_region.
            click_point = (found_work[0] + search_region[0], found_work[1] + search_region[1])
            GA.Click(click_point)
            time.sleep(0.1) # Brief pause after clicking.
        else:
            # If no images are found, pause briefly before the next screen capture.
            time.sleep(0.1)