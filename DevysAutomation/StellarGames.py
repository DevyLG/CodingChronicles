import customtkinter as ctk
from PIL import Image, ImageTk, ImageGrab
import threading
import time
import mss
import math
import json
import glob
import os
import keyboard
import cv2
import numpy as np

try:
    import pydirectinput
    pydirectinput.PAUSE = 0.05 
except ImportError:
    pydirectinput = None

class PixelAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.running = False
        self.bot_thread = None
        
        self.active_rules = [] 
        self.selected_rule_index = None 

        # Selection Vars
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        self.capture_mode = "pixel"

        # 1. Window Setup
        self.title("Devy's Multi-Rule Automation")
        self.geometry("900x800") 
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color="#333333") 

        # 2. Header
        self.header_label = ctk.CTkLabel(
            self, text="Devy's Multi-Rule Engine", 
            font=("Arial", 28, "bold"), text_color="#00FFFF"
        )
        self.header_label.pack(pady=(10, 10))

        # 3. Tabs
        self.tabview = ctk.CTkTabview(self, width=850, height=700, fg_color="#2b2b2b")
        self.tabview.pack(padx=20, pady=10)
        self.tab_capture = self.tabview.add("1. Capture Ingredients")
        self.tab_logic = self.tabview.add("2. Build Logic Chain")

        self.setup_capture_tab()
        self.setup_logic_tab()

    # =======================================================
    # TAB 1: CAPTURE
    # =======================================================
    def setup_capture_tab(self):
        frame = ctk.CTkFrame(self.tab_capture, fg_color="transparent")
        frame.pack(fill="both", padx=20, pady=20)

        # --- PIXEL ---
        ctk.CTkLabel(frame, text="-- OPTION A: PIXEL DETECT --", text_color="gray").pack(anchor="w")
        x_row = self.create_input_row(frame, "X:", "X Coord")
        self.create_action_button(x_row, "Pick Pixel", lambda: self.start_overlay("pixel")).pack(side="left", padx=10)
        self.create_input_row(frame, "Y:", "Y Coord")
        rgb_row = self.create_input_row(frame, "RGB:", "255, 0, 0")
        self.create_action_button(rgb_row, "Pick Color", lambda: self.start_overlay("pixel")).pack(side="left", padx=10)

        # --- IMAGE ---
        ctk.CTkLabel(frame, text="-- OPTION B: IMAGE DETECT --", text_color="gray").pack(anchor="w", pady=(20,0))
        img_row = ctk.CTkFrame(frame, fg_color="transparent")
        img_row.pack(anchor="w", pady=5)
        ctk.CTkLabel(img_row, text="Image:", font=("Arial", 20, "bold"), text_color="#00FFFF", width=60, anchor="w").pack(side="left")
        self.entry_Image = ctk.CTkEntry(img_row, placeholder_text="Path to image...", width=200, fg_color="#2b2b2b", text_color="white", border_color="#00FFFF")
        self.entry_Image.pack(side="left", padx=10)
        self.create_action_button(img_row, "Capture Region", lambda: self.start_overlay("image")).pack(side="left", padx=10)

        # --- SAVE ---
        ctk.CTkLabel(frame, text="-- SAVE INGREDIENT --", text_color="gray").pack(anchor="w", pady=(20,0))
        self.create_input_row(frame, "Name:", "e.g. start_btn")

        self.save_btn = ctk.CTkButton(
            self.tab_capture, text="SAVE DETECTOR (.json)", width=200, height=40,
            fg_color="#00AA00", hover_color="#00FF00", font=("Arial", 16, "bold"),
            command=self.save_new_profile
        )
        self.save_btn.pack(pady=20)
        self.save_status = ctk.CTkLabel(self.tab_capture, text="", text_color="yellow")
        self.save_status.pack()

    # =======================================================
    # TAB 2: LOGIC CHAIN
    # =======================================================
    def setup_logic_tab(self):
        self.logic_frame = ctk.CTkFrame(self.tab_logic, fg_color="transparent")
        self.logic_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- LEFT COLUMN: RULE LIST ---
        left_col = ctk.CTkFrame(self.logic_frame, width=300, fg_color="#222222")
        left_col.pack(side="left", fill="y", padx=5)

        ctk.CTkLabel(left_col, text="Active Rules:", font=("Arial", 18, "bold"), text_color="#00FFFF").pack(pady=10)
        
        self.profile_dropdown = ctk.CTkOptionMenu(left_col, values=["No Profiles"], width=200)
        self.profile_dropdown.pack(pady=5)
        ctk.CTkButton(left_col, text="+ Add Detection Rule", fg_color="#00AA00", command=self.add_rule_to_list).pack(pady=5)
        ctk.CTkButton(left_col, text="↻ Refresh Files", width=100, command=self.refresh_profiles).pack(pady=5)
        
        ctk.CTkLabel(left_col, text="Your Logic Chain:", text_color="gray").pack(pady=(20,5))
        
        self.rule_scroll = ctk.CTkScrollableFrame(left_col, width=250, height=300, fg_color="#1a1a1a")
        self.rule_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # --- RIGHT COLUMN: ACTION EDITOR ---
        right_col = ctk.CTkFrame(self.logic_frame, fg_color="transparent")
        right_col.pack(side="left", fill="both", expand=True, padx=5)

        self.editor_label = ctk.CTkLabel(right_col, text="Select a Rule to Edit Actions", font=("Arial", 18, "bold"))
        self.editor_label.pack(pady=10)

        # Action Builder
        controls = ctk.CTkFrame(right_col, fg_color="#333333", border_color="#00FFFF", border_width=1)
        controls.pack(fill="x", pady=10)

        self.action_type = ctk.CTkOptionMenu(
            controls, 
            values=["Press Key", "Type Text", "Wait (ms)", "Click Found Spot", "Click Custom (X,Y)"],
            width=150
        )
        self.action_type.pack(side="left", padx=5, pady=10)
        
        self.action_value = ctk.CTkEntry(controls, placeholder_text="Value", width=150)
        self.action_value.pack(side="left", padx=5, pady=10)
        
        ctk.CTkButton(controls, text="Add Action", width=80, fg_color="#00AA00", command=self.add_action_to_rule).pack(side="left", padx=5)

        # Action List Display
        self.action_scroll = ctk.CTkScrollableFrame(right_col, height=200, fg_color="#1a1a1a")
        self.action_scroll.pack(fill="both", expand=True)

        # START / STOP
        btn_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        btn_frame.pack(pady=20)
        self.start_btn = ctk.CTkButton(btn_frame, text="START ALL", width=120, height=40, fg_color="#00AA00", font=("Arial", 16, "bold"), command=self.start_automation)
        self.start_btn.pack(side="left", padx=10)
        self.stop_btn = ctk.CTkButton(btn_frame, text="STOP", width=120, height=40, fg_color="#AA0000", state="disabled", command=self.stop_automation)
        self.stop_btn.pack(side="left", padx=10)

        self.refresh_profiles()

    # =======================================================
    # LOGIC: MANAGING RULES
    # =======================================================
    def refresh_profiles(self):
        files = glob.glob("*.json")
        if files:
            self.profile_dropdown.configure(values=files)
            self.profile_dropdown.set(files[0])
        else:
            self.profile_dropdown.configure(values=["No Profiles"])

    def add_rule_to_list(self):
        filename = self.profile_dropdown.get()
        if filename == "No Profiles": return

        try:
            with open(filename, "r") as f:
                data = json.load(f)
            
            new_rule = {
                "name": filename,
                "data": data, 
                "actions": [] 
            }
            self.active_rules.append(new_rule)
            self.render_rule_list()
        except Exception as e:
            print(f"Error loading rule: {e}")

    def render_rule_list(self):
        for widget in self.rule_scroll.winfo_children():
            widget.destroy()

        for index, rule in enumerate(self.active_rules):
            row = ctk.CTkFrame(self.rule_scroll, fg_color="#333333")
            row.pack(fill="x", pady=2)
            
            btn_text = f"{index+1}. {rule['name']}"
            if rule['data'].get('type') == 'image': btn_text += " (IMG)"
            else: btn_text += " (PXL)"

            cmd = lambda i=index: self.select_rule(i)
            ctk.CTkButton(row, text=btn_text, anchor="w", fg_color="transparent", border_width=1, border_color="gray", command=cmd).pack(side="left", fill="x", expand=True)

            del_cmd = lambda i=index: self.delete_rule(i)
            ctk.CTkButton(row, text="X", width=30, fg_color="#AA0000", command=del_cmd).pack(side="right")

    def delete_rule(self, index):
        self.active_rules.pop(index)
        if self.selected_rule_index == index:
            self.selected_rule_index = None
            self.render_action_list() 
        self.render_rule_list()

    def select_rule(self, index):
        self.selected_rule_index = index
        self.editor_label.configure(text=f"Editing: {self.active_rules[index]['name']}", text_color="#00FFFF")
        self.render_action_list()

    # =======================================================
    # LOGIC: ACTIONS (Added Move Up/Down)
    # =======================================================
    def add_action_to_rule(self):
        if self.selected_rule_index is None: return

        atype = self.action_type.get()
        aval = self.action_value.get()
        
        self.active_rules[self.selected_rule_index]["actions"].append({
            "type": atype, "value": aval
        })
        self.render_action_list()
        self.action_value.delete(0, "end")

    def move_action_up(self, index):
        if self.selected_rule_index is None: return
        actions = self.active_rules[self.selected_rule_index]["actions"]
        if index > 0:
            actions[index], actions[index-1] = actions[index-1], actions[index]
            self.render_action_list()

    def move_action_down(self, index):
        if self.selected_rule_index is None: return
        actions = self.active_rules[self.selected_rule_index]["actions"]
        if index < len(actions) - 1:
            actions[index], actions[index+1] = actions[index+1], actions[index]
            self.render_action_list()

    def render_action_list(self):
        for widget in self.action_scroll.winfo_children():
            widget.destroy()
            
        if self.selected_rule_index is None: return

        actions = self.active_rules[self.selected_rule_index]["actions"]
        
        for idx, act in enumerate(actions):
            row = ctk.CTkFrame(self.action_scroll, fg_color="#2b2b2b")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{idx+1}. {act['type']} [{act['value']}]", anchor="w", width=300).pack(side="left", padx=10)
            
            # --- MOVE UP ---
            if idx > 0:
                ctk.CTkButton(row, text="↑", width=30, fg_color="#555555", command=lambda i=idx: self.move_action_up(i)).pack(side="left", padx=2)
            else:
                ctk.CTkLabel(row, text="   ", width=30).pack(side="left", padx=2) 

            # --- MOVE DOWN ---
            if idx < len(actions) - 1:
                ctk.CTkButton(row, text="↓", width=30, fg_color="#555555", command=lambda i=idx: self.move_action_down(i)).pack(side="left", padx=2)
            else:
                ctk.CTkLabel(row, text="   ", width=30).pack(side="left", padx=2) 

            # --- DELETE ---
            cmd = lambda i=idx: self.delete_action(i)
            ctk.CTkButton(row, text="X", width=30, fg_color="#550000", command=cmd).pack(side="right", padx=5)

    def delete_action(self, action_index):
        if self.selected_rule_index is not None:
            self.active_rules[self.selected_rule_index]["actions"].pop(action_index)
            self.render_action_list()

    # =======================================================
    # THE AUTOMATION ENGINE
    # =======================================================
    def start_automation(self):
        if not self.active_rules: return
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        self.bot_thread = threading.Thread(target=self.automation_loop)
        self.bot_thread.daemon = True
        self.bot_thread.start()

    def stop_automation(self):
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def automation_loop(self):
        print("Bot Started. Running Logic Chain...")
        
        # Pre-load all image templates
        for rule in self.active_rules:
            if rule['data'].get('type') == 'image':
                path = rule['data']['image_path']
                try:
                    img = cv2.imread(path, 0)
                    rule['template'] = img
                    h, w = img.shape
                    rule['size'] = (w, h)
                except:
                    print(f"Failed to load image: {path}")

        with mss.mss() as sct:
            while self.running:
                for rule in self.active_rules:
                    found = False
                    found_x, found_y = 0, 0
                    data = rule['data']

                    # --- PIXEL CHECK ---
                    if data.get('type') == 'pixel':
                        try:
                            monitor = {"top": int(data["y"]), "left": int(data["x"]), "width": 1, "height": 1}
                            img = sct.grab(monitor)
                            pixel = img.pixel(0, 0)
                            target = list(map(int, data["rgb"].split(',')))
                            diff = math.sqrt(sum((a - b) ** 2 for a, b in zip(pixel, target)))
                            if diff < 20:
                                found = True
                                found_x, found_y = int(data["x"]), int(data["y"])
                        except: pass

                    # --- IMAGE CHECK ---
                    elif data.get('type') == 'image' and 'template' in rule:
                        try:
                            monitor = sct.monitors[1]
                            sct_img = np.array(sct.grab(monitor))
                            gray_screen = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2GRAY)
                            res = cv2.matchTemplate(gray_screen, rule['template'], cv2.TM_CCOEFF_NORMED)
                            loc = np.where(res >= 0.8) 
                            
                            if len(loc[0]) > 0:
                                found = True
                                pt = list(zip(*loc[::-1]))[0] 
                                w, h = rule['size']
                                found_x = int(pt[0] + w/2)
                                found_y = int(pt[1] + h/2)
                        except: pass

                    # --- EXECUTE ACTIONS ---
                    if found:
                        print(f"Rule '{rule['name']}' matched! Executing actions...")
                        for action in rule['actions']:
                            atype = action['type']
                            aval = action['value']

                            if atype == "Press Key":
                                if pydirectinput: pydirectinput.press(aval)
                            
                            elif atype == "Type Text":
                                try: keyboard.write(str(aval), delay=0.05)
                                except: pass
                            
                            elif atype == "Wait (ms)":
                                time.sleep(float(aval) / 1000)
                            
                            elif atype == "Click Found Spot":
                                if pydirectinput:
                                    pydirectinput.moveTo(found_x, found_y)
                                    pydirectinput.click()

                            elif atype == "Click Custom (X,Y)":
                                try:
                                    coords = aval.split(',')
                                    cx = int(coords[0].strip())
                                    cy = int(coords[1].strip())
                                    if pydirectinput:
                                        pydirectinput.moveTo(cx, cy)
                                        pydirectinput.click()
                                except: print("Invalid Coords")
                        
                        time.sleep(0.5)

                time.sleep(0.1)

    # =======================================================
    # OVERLAYS & FILE SAVING
    # =======================================================
    def start_overlay(self, mode):
        self.capture_mode = mode
        self.withdraw()
        self.after(200, self.launch_overlay)

    def launch_overlay(self):
        self.screenshot_img = ImageGrab.grab()
        self.tk_image = ImageTk.PhotoImage(self.screenshot_img)
        self.overlay = ctk.CTkToplevel()
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.canvas = ctk.CTkCanvas(self.overlay, width=self.screenshot_img.width, height=self.screenshot_img.height, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
        
        if self.capture_mode == "pixel":
            self.canvas.bind("<Button-1>", self.on_pixel_click)
        else:
            self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
            self.canvas.bind("<B1-Motion>", self.on_drag_motion)
            self.canvas.bind("<ButtonRelease-1>", self.on_drag_release)
        self.canvas.bind("<Button-3>", lambda e: (self.overlay.destroy(), self.deiconify()))

    def on_pixel_click(self, event):
        x, y = event.x, event.y
        rgb = self.screenshot_img.getpixel((x, y))
        self.overlay.destroy()
        self.deiconify()
        self.entry_X.delete(0, "end"); self.entry_X.insert(0, str(x))
        self.entry_Y.delete(0, "end"); self.entry_Y.insert(0, str(y))
        self.entry_RGB.delete(0, "end"); self.entry_RGB.insert(0, f"{rgb[0]}, {rgb[1]}, {rgb[2]}")
        self.entry_Image.delete(0, "end")

    def on_drag_start(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='cyan', width=2)

    def on_drag_motion(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_drag_release(self, event):
        self.overlay.destroy()
        self.deiconify()
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        crop = self.screenshot_img.crop((x1, y1, x2, y2))
        if not os.path.exists("images"): os.makedirs("images")
        filename = f"images/cap_{int(time.time())}.png"
        crop.save(filename)
        self.entry_Image.delete(0, "end"); self.entry_Image.insert(0, filename)
        self.entry_X.delete(0, "end"); self.entry_Y.delete(0, "end"); self.entry_RGB.delete(0, "end")

    def save_new_profile(self):
        name = self.entry_Name.get()
        if not name: return
        image_path = self.entry_Image.get()
        if image_path:
            data = {"type": "image", "image_path": image_path}
        else:
            data = {"type": "pixel", "x": self.entry_X.get(), "y": self.entry_Y.get(), "rgb": self.entry_RGB.get()}
        
        with open(f"{name}.json", "w") as f: json.dump(data, f)
        self.save_status.configure(text=f"Saved {name}.json!", text_color="#00FF00")
        self.refresh_profiles()

    # --- HELPERS ---
    def create_input_row(self, parent, label_text, placeholder):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(anchor="w", pady=5)
        ctk.CTkLabel(row_frame, text=label_text, font=("Arial", 20, "bold"), text_color="#00FFFF", width=60, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row_frame, placeholder_text=placeholder, width=200, fg_color="#2b2b2b", text_color="white", border_color="#00FFFF")
        entry.pack(side="left", padx=10)
        setattr(self, f"entry_{label_text.replace(':', '')}", entry)
        return row_frame

    def create_action_button(self, parent, text, command):
        return ctk.CTkButton(parent, text=text, width=100, fg_color="#444444", hover_color="#555555", border_color="#00FFFF", border_width=2, text_color="#00FFFF", command=command)

if __name__ == "__main__":
    app = PixelAutomationApp()
    app.mainloop()