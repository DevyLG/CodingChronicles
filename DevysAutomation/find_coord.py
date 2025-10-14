import pyautogui
import time

print("This script helps you find the coordinates for a screen region.")
print("="*60)

# Get the top-left corner
print("\nMove your mouse to the TOP-LEFT corner of the region you want to capture.")
print("You have 5 seconds...")
time.sleep(5)
left, top = pyautogui.position()
print(f"✅ Top-Left corner captured: (left={left}, top={top})")

# Get the bottom-right corner
print("\nNow, move your mouse to the BOTTOM-RIGHT corner of that same region.")
print("You have 5 seconds...")
time.sleep(5)
right, bottom = pyautogui.position()
print(f"✅ Bottom-Right corner captured: (right={right}, bottom={bottom})")

# Calculate width and height
width = right - left
height = bottom - top

# Display the final result
print("\n🎉 Success! Here are your coordinates:")
print(f"Your region is: ({left}, {top}, {width}, {height})")
print("="*60)
print("Copy this tuple and paste it into your main script.")