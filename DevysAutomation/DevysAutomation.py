import cv2
import mss
import numpy as np
import pyautogui
import time
import os

def locate(image_configs, default_threshold=0.8, default_method=cv2.TM_CCOEFF_NORMED, region=None, debug_mode=False, screen_capture=None, grayscale=False):
    """Finds an image, using per-image config to decide on grayscale or color search.

    Args:
        image_configs (str | list): A single path, list of paths, or list of dictionaries.
                                    Dictionaries can contain a 'grayscale': True/False key to override the main grayscale arg.
        default_threshold (float): The fallback confidence level for matching (0.0 to 1.0).
        default_method (int): The fallback OpenCV matching method.
        region (tuple): A tuple (x, y, width, height) to limit the search area.
        debug_mode (bool): If True, displays a window with the visual search result.
        screen_capture (np.ndarray): An optional, pre-captured BGR screenshot to search within.
        grayscale (bool): The default search mode. If True, performs search in grayscale. Can be overridden per image.
    """
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
    
    if screen_capture is None:
        with mss.mss() as sct:
            monitor = {"top": 0, "left": 0, "width": pyautogui.size().width, "height": pyautogui.size().height}
            if region:
                monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
            screen_capture_img = sct.grab(monitor)
            screen = cv2.cvtColor(np.array(screen_capture_img), cv2.COLOR_BGRA2BGR)
    else:
        screen = screen_capture

    for config in configs:
        image_path = config.get('path')
        if not image_path:
            continue
        
        template = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if template is None:
            print(f"Warning: Could not read image at {image_path}. Skipping.")
            continue

        use_grayscale = config.get('grayscale', grayscale)

        search_screen = screen.copy()
        
        if use_grayscale:
            search_screen = cv2.cvtColor(search_screen, cv2.COLOR_BGR2GRAY)
            if len(template.shape) == 3:
                search_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                search_template = template
        else:
            if len(template.shape) == 3 and template.shape[2] == 4:
                search_template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
            else:
                search_template = template

        template_height, template_width = search_template.shape[:2]
        
        if search_template.shape[0] > search_screen.shape[0] or search_template.shape[1] > search_screen.shape[1]:
            continue

        threshold = config.get('threshold', default_threshold)
        method = config.get('method', default_method)
        result = cv2.matchTemplate(search_screen, search_template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            confidence = 1.0 - min_val
            top_left = min_loc
        else:
            confidence = max_val
            top_left = max_loc

        if confidence >= threshold:
            center_x = top_left[0] + template_width // 2
            center_y = top_left[1] + template_height // 2

            show_debug_window = config.get('debug_mode', debug_mode)
            if show_debug_window:
                bottom_right = (top_left[0] + template_width, top_left[1] + template_height)
                
                cv2.rectangle(screen, top_left, bottom_right, (0, 255, 0), 2) 
                cv2.circle(screen, (center_x, center_y), 5, (0, 0, 255), -1)
                print(f"DEBUG: Found '{image_path}' with confidence {confidence:.2f}")
                
                window_title = f"Debug: Found '{os.path.basename(image_path)}' (Conf: {confidence:.2f})"
                cv2.imshow(window_title, screen)
                cv2.waitKey(0)
                cv2.destroyAllWindows()


            if region:
                center_x += region[0]
                center_y += region[1]
            return (center_x, center_y)
            
    return None

def locateAll(image_path, threshold=0.8, method=cv2.TM_CCOEFF_NORMED, grayscale=True, region=None):
    """Finds all occurrences of an image on the screen.

    Args:
        image_path (str): The path to the image file to locate.
        threshold (float): The confidence level for the match (0.0 to 1.0).
        method (int): The OpenCV template matching method.
        grayscale (bool): If True, performs the search in grayscale.
        region (tuple): A tuple (x, y, width, height) to limit the search area.

    Returns:
        list: A list of (x, y) tuples for each match found. Returns an empty list if none.
    """
    template = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if template is None:
        return []

    if len(template.shape) == 3 and template.shape[2] == 4:
        template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)

    template_height, template_width = template.shape[:2]

    with mss.mss() as sct:
        monitor = {"top": 0, "left": 0, "width": pyautogui.size().width, "height": pyautogui.size().height}
        if region:
            monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
        screen_capture_img = sct.grab(monitor)
        screen = np.array(screen_capture_img)
        screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)

    if grayscale:
        screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(screen, template, method)
    locations = np.where(result >= threshold)
    
    rectangles = []
    for pt in zip(*locations[::-1]):
        rect = [int(pt[0]), int(pt[1]), template_width, template_height]
        rectangles.append(rect)

    boxes, weights = cv2.groupRectangles(rectangles, 1, 0.5)
    
    centers = []
    for (x, y, w, h) in boxes:
        center_x = x + w // 2
        center_y = y + h // 2
        if region:
            center_x += region[0]
            center_y += region[1]
        centers.append((center_x, center_y))
        
    return centers

# Moves the mouse to a set of coordinates and clicks.
def Click(coords, button='left', duration=0.1):
    """Performs a mouse click at the given coordinates.

    Args:
        coords (tuple): A tuple (x, y) for the click coordinates.
        button (str): The mouse button to click ('left', 'right', 'middle').
        duration (float): The time in seconds to move the mouse to the coordinates.
    """
    if coords:
        pyautogui.moveTo(coords[0], coords[1], duration=duration)
        pyautogui.click(button=button)

# Pauses the script until a specific image appears on the screen.
def waitForImage(image_configs, timeout=30, interval=0.5, **kwargs):
    """Waits for a specified image to appear on the screen.

    Args:
        image_configs: The image configuration(s) to look for (passed to locate).
        timeout (int): The maximum number of seconds to wait.
        interval (float): The time in seconds between each check.
        **kwargs: Other arguments to pass to the locate function (e.g., region).

    Returns:
        tuple | None: The coordinates of the found image, or None if it times out.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        found_coords = locate(image_configs, **kwargs)
        if found_coords:
            return found_coords
        time.sleep(interval)
    return None

# Pauses the script until a specific image is no longer on the screen.
def waitToDisappear(image_configs, timeout=30, interval=0.5, **kwargs):
    """Waits for a specified image to disappear from the screen.

    Args:
        image_configs: The image configuration(s) to check for (passed to locate).
        timeout (int): The maximum number of seconds to wait.
        interval (float): The time in seconds between each check.
        **kwargs: Other arguments to pass to the locate function (e.g., region).

    Returns:
        bool: True if the image disappeared, False if it timed out.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not locate(image_configs, **kwargs):
            return True
        time.sleep(interval)
    return False

