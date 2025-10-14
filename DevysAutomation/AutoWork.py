import DevysAutomation as GA
import cv2
import time
import pyautogui as pag
import keyboard as kb
import mss
import numpy as np


# This is an example script to automate SuperLife.




DEBUG = False


# --- Configuration ---
# Default is color search. You can override per image with 'grayscale': True/False
wait_image = [{'path': 'cantwork.png', 'threshold': 0.90, 'method': cv2.TM_CCOEFF_NORMED}]
click_list = [
    {'path': 'okay.png', 'threshold': 0.90, 'method': cv2.TM_CCOEFF_NORMED},
    {'path': 'work_button_hover.png', 'threshold': 0.72, 'method': cv2.TM_CCOEFF_NORMED, 'grayscale': True},
    {'path': 'work_button.png', 'threshold': 0.60, 'method': cv2.TM_CCOEFF_NORMED, 'grayscale': False},
]

# --- IMPORTANT: DEFINE A SEARCH REGION ---
# Searching a small area is much faster than the whole screen.
# Adjust these coordinates to cover all your buttons.
search_region = (346, 420, 1181, 420) # Example: (left, top, width, height)
monitor_region = {"top": search_region[1], "left": search_region[0], "width": search_region[2], "height": search_region[3]}

def slurp_soda():
    kb.press_and_release('3')
    time.sleep(0.25)
    pag.click(646, 456)
    kb.press_and_release('3')
    time.sleep(0.1)
    kb.press_and_release('e')

print("Starting automation. Press Ctrl+C to stop.")

# --- Main Loop (Optimized) ---
with mss.mss() as sct:
    while True:
        # 1. Take ONE screenshot of the region.
        screen_capture_img = sct.grab(monitor_region)
        screen_capture = cv2.cvtColor(np.array(screen_capture_img), cv2.COLOR_BGRA2BGR)

        # 2. Search for the "wait" image in that screenshot.
        is_waiting = GA.locate(
            image_configs=wait_image,
            screen_capture=screen_capture
        )

        if is_waiting is not None:
            slurp_soda()
            continue

        # 3. If not waiting, search for the "click" images in the SAME screenshot.
        found_work = GA.locate(
            image_configs=click_list,
            screen_capture=screen_capture # Pass the same screenshot again
        )
        
        if found_work is not None:

            click_point = (found_work[0] + search_region[0], found_work[1] + search_region[1])
            GA.Click(click_point)
            time.sleep(0.1)
        else:
            time.sleep(0.1)