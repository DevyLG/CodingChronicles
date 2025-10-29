"""
DevysAutomation (Game Automation) Module

This module provides a set of functions for automating interactions with the screen,
primarily designed for game automation but useful for any GUI automation task.

It uses OpenCV for image recognition to find and interact with elements on the screen.

Core functionalities include:
-   Locating single or multiple instances of images on the screen.
-   Performing mouse clicks.
-   Waiting for specific images to appear or disappear.

The main function is `locate()`, which is highly configurable and can search for
images in color or grayscale, within a specific region, and even on a pre-captured
screenshot for optimization.

Dependencies:
-   opencv-python
-   mss
-   numpy
-   pyautogui

Usage:
Import the module and use its functions to build your automation scripts:

    import DevysAutomation as GA

    # Find the 'start_button.png' and click it
    start_button_coords = GA.locate('start_button.png', threshold=0.9)
    if start_button_coords:
        GA.Click(start_button_coords)

"""
import cv2
import mss
import numpy as np
import pyautogui
import time
import os

def locate(image_configs, default_threshold=0.8, default_method=cv2.TM_CCOEFF_NORMED, region=None, debug_mode=False, screen_capture=None, grayscale=False):
    """Finds the first occurrence of an image from a list on the screen, with flexible search options.

    This is the primary workhorse function. It can take a single image path, a list of paths,
    or a list of detailed configuration dictionaries. This allows for fine-tuning the search
    parameters (like threshold, grayscale) for each image individually.

    Args:
        image_configs (str | list): A configuration for the images to find.
            - str: Path to a single image file.
            - list of str: A list of image file paths to search for sequentially.
            - list of dict: A list of dictionaries, where each dict configures a search.
                - 'path' (str): Path to the image file.
                - 'threshold' (float, optional): Confidence level for this specific image.
                - 'method' (int, optional): OpenCV matching method for this image.
                - 'grayscale' (bool, optional): Override the top-level grayscale argument.
                - 'debug_mode' (bool, optional): Override the top-level debug_mode argument.
        default_threshold (float): The fallback confidence level (0.0 to 1.0) if not set per image.
        default_method (int): The fallback OpenCV matching method if not set per image.
        region (tuple, optional): A tuple (left, top, width, height) to limit the search area.
                                  Searching a smaller region is significantly faster.
        debug_mode (bool): If True, displays a window showing the match and confidence level.
        screen_capture (np.ndarray, optional): A pre-captured screenshot (in BGR format) to search within.
                                             This is a key optimization to avoid re-capturing the screen.
        grayscale (bool): The default search mode. If True, performs the search in grayscale unless overridden.

    Returns:
        tuple | None: A tuple (x, y) of the center coordinates of the first found image, relative to the full screen.
                      Returns None if no image is found that meets the threshold.
    """
    # --- 1. Normalize image_configs into a list of dictionaries ---
    configs = []
    if isinstance(image_configs, str):
        configs.append({'path': image_configs})
    elif isinstance(image_configs, list):
        if all(isinstance(item, str) for item in image_configs):
            for path in image_configs:
                configs.append({'path': path})
        elif all(isinstance(item, dict) for item in image_configs):
            configs = image_configs
        else:
            print("Error: image_configs list must contain all strings or all dictionaries.")
            return None
    
    # --- 2. Capture the screen if not provided ---
    if screen_capture is None:
        with mss.mss() as sct:
            # If no region is specified, capture the entire screen.
            monitor = {"top": 0, "left": 0, "width": pyautogui.size().width, "height": pyautogui.size().height}
            if region:
                monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
            screen_capture_img = sct.grab(monitor)
            # Convert the raw BGRA image from mss to a BGR image for OpenCV.
            screen = cv2.cvtColor(np.array(screen_capture_img), cv2.COLOR_BGRA2BGR)
    else:
        # Use the pre-captured image.
        screen = screen_capture

    # --- 3. Iterate through each image configuration and search ---
    for config in configs:
        image_path = config.get('path')
        if not image_path:
            continue
        
        # Load the template image to be searched for.
        template = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if template is None:
            print(f"Warning: Could not read image at {image_path}. Skipping.")
            continue

        # Decide whether to use grayscale for this specific image.
        use_grayscale = config.get('grayscale', grayscale)

        search_screen = screen.copy()
        
        # --- 4. Prepare screen and template for matching (Color vs. Grayscale) ---
        if use_grayscale:
            search_screen = cv2.cvtColor(search_screen, cv2.COLOR_BGR2GRAY)
            # Convert template to grayscale if it has color channels.
            if len(template.shape) == 3:
                search_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                search_template = template # Template is already grayscale.
        else:
            # Ensure template is in BGR format for color matching.
            if len(template.shape) == 3 and template.shape[2] == 4: # BGRA to BGR
                search_template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
            else:
                search_template = template

        template_height, template_width = search_template.shape[:2]
        
        # Optimization: Skip if the template is larger than the screen capture.
        if search_template.shape[0] > search_screen.shape[0] or search_template.shape[1] > search_screen.shape[1]:
            continue

        # --- 5. Perform Template Matching ---
        threshold = config.get('threshold', default_threshold)
        method = config.get('method', default_method)
        result = cv2.matchTemplate(search_screen, search_template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Determine confidence and location based on the matching method.
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            # For these methods, a lower value means a better match.
            confidence = 1.0 - min_val
            top_left = min_loc
        else:
            # For other methods, a higher value means a better match.
            confidence = max_val
            top_left = max_loc

        # --- 6. Check if the match is good enough ---
        if confidence >= threshold:
            # Calculate the center of the found region.
            center_x = top_left[0] + template_width // 2
            center_y = top_left[1] + template_height // 2

            # --- 7. (Optional) Display Debug Window ---
            show_debug_window = config.get('debug_mode', debug_mode)
            if show_debug_window:
                bottom_right = (top_left[0] + template_width, top_left[1] + template_height)
                # Draw a green rectangle around the match.
                cv2.rectangle(screen, top_left, bottom_right, (0, 255, 0), 2) 
                # Draw a red circle at the center point.
                cv2.circle(screen, (center_x, center_y), 5, (0, 0, 255), -1)
                print(f"DEBUG: Found '{image_path}' with confidence {confidence:.2f}")
                
                window_title = f"Debug: Found '{os.path.basename(image_path)}' (Conf: {confidence:.2f})"
                cv2.imshow(window_title, screen)
                cv2.waitKey(0) # Wait for a key press to close the window.
                cv2.destroyAllWindows()

            # If a region was used, convert coordinates back to be relative to the full screen.
            if region:
                center_x += region[0]
                center_y += region[1]
            
            return (center_x, center_y) # Return the coordinates of the first match.
            
    return None # Return None if no matches were found.


def locateAll(image_path, threshold=0.8, method=cv2.TM_CCOEFF_NORMED, grayscale=True, region=None):
    """Finds all occurrences of a given image on the screen.

    This function is useful for finding multiple targets of the same type, like all enemy units
    or all resource nodes.

    Args:
        image_path (str): The path to the image file to locate.
        threshold (float): The confidence level for what constitutes a match (0.0 to 1.0).
        method (int): The OpenCV template matching method to use.
        grayscale (bool): If True, performs the search in grayscale for speed.
        region (tuple, optional): A tuple (x, y, width, height) to limit the search area.

    Returns:
        list: A list of (x, y) tuples for the center of each match found.
              Returns an empty list if no matches are found.
    """
    template = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        print(f"Warning: Could not read image at {image_path}. Skipping.")
        return []

    # Ensure template is in a format that can be compared with the screen.
    if len(template.shape) == 3 and template.shape[2] == 4:
        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

    template_height, template_width = template.shape[:2]

    # Capture the screen.
    with mss.mss() as sct:
        monitor = {"top": 0, "left": 0, "width": pyautogui.size().width, "height": pyautogui.size().height}
        if region:
            monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
        screen_capture_img = sct.grab(monitor)
        screen = np.array(screen_capture_img)
        screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

    # Convert both screen and template to grayscale if required.
    if grayscale:
        screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    # Find all locations where the match exceeds the threshold.
    result = cv2.matchTemplate(screen, template, method)
    locations = np.where(result >= threshold)
    
    # Group overlapping rectangles to avoid multiple detections of the same object.
    rectangles = []
    for pt in zip(*locations[::-1]): # Switch (row, col) to (x, y)
        rect = [int(pt[0]), int(pt[1]), template_width, template_height]
        rectangles.append(rect)

    # groupRectangles helps merge overlapping boxes.
    boxes, weights = cv2.groupRectangles(rectangles, 1, 0.5)
    
    centers = []
    for (x, y, w, h) in boxes:
        center_x = x + w // 2
        center_y = y + h // 2
        # Adjust coordinates if a search region was used.
        if region:
            center_x += region[0]
            center_y += region[1]
        centers.append((center_x, center_y))
        
    return centers

def Click(coords, button='left', duration=0.1):
    """Moves the mouse to the given coordinates and performs a click.

    A convenience wrapper around pyautogui's moveTo and click functions.

    Args:
        coords (tuple): A tuple (x, y) for the screen coordinates to click.
        button (str): The mouse button to click ('left', 'right', 'middle').
        duration (float): The time in seconds for the mouse to move to the coordinates.
    """
    if coords:
        pyautogui.moveTo(coords[0], coords[1], duration=duration)
        pyautogui.click(button=button)

def waitForImage(image_configs, timeout=30, interval=0.5, **kwargs):
    """Pauses the script until a specific image appears on the screen.

    This is useful for waiting for a loading screen to finish or for a specific
    button to become visible.

    Args:
        image_configs: The image configuration(s) to look for (passed directly to `locate`).
        timeout (int): The maximum number of seconds to wait before giving up.
        interval (float): The time in seconds to wait between each search attempt.
        **kwargs: Other keyword arguments to pass to the `locate` function (e.g., region, threshold).

    Returns:
        tuple | None: The coordinates (x, y) of the found image, or None if it times out.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        found_coords = locate(image_configs, **kwargs)
        if found_coords:
            return found_coords
        time.sleep(interval)
    print(f"Timeout: Image not found after {timeout} seconds.")
    return None

def waitToDisappear(image_configs, timeout=30, interval=0.5, **kwargs):
    """Pauses the script until a specific image is no longer visible on the screen.

    This is useful for waiting for a progress bar to disappear or a temporary
    pop-up to close.

    Args:
        image_configs: The image configuration(s) to check for (passed directly to `locate`).
        timeout (int): The maximum number of seconds to wait before giving up.
        interval (float): The time in seconds to wait between each search attempt.
        **kwargs: Other keyword arguments to pass to the `locate` function (e.g., region, threshold).

    Returns:
        bool: True if the image disappeared within the timeout, False otherwise.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not locate(image_configs, **kwargs):
            return True # Image has disappeared.
        time.sleep(interval)
    print(f"Timeout: Image was still visible after {timeout} seconds.")
    return False