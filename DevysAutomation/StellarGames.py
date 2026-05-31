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
import random

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
        self.last_capture_region = None

        # 1. Window Setup
        self.title("Stellar Games - Automation Engine Pro")
        self.geometry("1180x880") 
        self.minsize(1050, 750)
        ctk.set_appearance_mode("Dark")
        
        # Color Palette Design
        self.configure(fg_color="#0b0b0f") # Ultra dark background
        
        # Custom Theme Colors
        self.color_bg_card = "#14141d"
        self.color_border = "#222232"
        self.color_accent = "#00F0FF" # Cyan neon
        self.color_success = "#00E676" # Green neon
        self.color_danger = "#FF5252" # Red neon
        self.color_text_muted = "#8a8a9e"

        # Build UI Structure
        self.create_header()
        self.create_main_layout()
        self.create_log_console()
        
        # Load initially available profiles
        self.refresh_profiles()
        
        self.log_message("Stellar Automation Engine loaded successfully.", "SUCCESS")
        if not pydirectinput:
            self.log_message("Warning: PyDirectInput not found. Click and keyboard actions might fail in DirectX games.", "WARNING")

    # =======================================================
    # UI COMPONENT: HEADER
    # =======================================================
    def create_header(self):
        # Header Container
        header_frame = ctk.CTkFrame(self, height=75, fg_color=self.color_bg_card, border_color=self.color_border, border_width=1)
        header_frame.pack(fill="x", padx=12, pady=(12, 6))
        header_frame.pack_propagate(False)

        # Title Block
        title_block = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_block.pack(side="left", padx=15, pady=8)
        
        title_lbl = ctk.CTkLabel(
            title_block, text="STELLAR AUTOMATION ENGINE", 
            font=("Arial", 22, "bold"), text_color=self.color_accent
        )
        title_lbl.pack(anchor="w")
        
        subtitle_lbl = ctk.CTkLabel(
            title_block, text="Advanced Pixel & Image Rule Sequence Engine", 
            font=("Arial", 11, "italic"), text_color=self.color_text_muted
        )
        subtitle_lbl.pack(anchor="w")

        # Top Controls Block
        ctrl_block = ctk.CTkFrame(header_frame, fg_color="transparent")
        ctrl_block.pack(side="right", padx=15, pady=8)

        # 1. LED Engine Status
        status_frame = ctk.CTkFrame(ctrl_block, fg_color="transparent")
        status_frame.pack(side="left", padx=15)
        
        self.led_indicator = ctk.CTkLabel(
            status_frame, text="", width=12, height=12, corner_radius=6, fg_color=self.color_danger
        )
        self.led_indicator.pack(side="left", padx=5)
        
        self.status_label = ctk.CTkLabel(
            status_frame, text="ENGINE STOPPED", 
            font=("Arial", 12, "bold"), text_color=self.color_danger
        )
        self.status_label.pack(side="left")

        # Separator Line
        ctk.CTkLabel(ctrl_block, text="|", font=("Arial", 18), text_color=self.color_border).pack(side="left", padx=10)

        # 2. Always On Top
        self.switch_always_on_top = ctk.CTkSwitch(
            ctrl_block, text="Always on Top", font=("Arial", 12),
            text_color="#FFFFFF", progress_color=self.color_accent, command=self.toggle_always_on_top
        )
        self.switch_always_on_top.pack(side="left", padx=10)

        # Anti-Detection: Humanize Mode Switch
        self.switch_humanize = ctk.CTkSwitch(
            ctrl_block, text="Humanize (Anti-Cheat)", font=("Arial", 12, "bold"),
            text_color=self.color_accent, progress_color=self.color_accent
        )
        self.switch_humanize.pack(side="left", padx=10)

        # 3. Loop Delay Slider
        slider_frame = ctk.CTkFrame(ctrl_block, fg_color="transparent")
        slider_frame.pack(side="left", padx=10)
        
        self.lbl_loop_speed = ctk.CTkLabel(
            slider_frame, text="Loop Delay: 100ms", font=("Arial", 11), text_color="#FFFFFF", width=120
        )
        self.lbl_loop_speed.pack(anchor="w")
        
        self.slider_loop_speed = ctk.CTkSlider(
            slider_frame, from_=10, to=2000, number_of_steps=199, width=120,
            progress_color=self.color_accent, command=self.on_loop_speed_change
        )
        self.slider_loop_speed.set(100)
        self.slider_loop_speed.pack(anchor="w")

        # Separator Line
        ctk.CTkLabel(ctrl_block, text="|", font=("Arial", 18), text_color=self.color_border).pack(side="left", padx=10)

        # 4. Save/Load Chain Buttons
        ctk.CTkButton(
            ctrl_block, text="Save Chain", width=85, height=28, 
            fg_color="#2b2b3d", hover_color="#3a3a52", text_color="#FFFFFF",
            font=("Arial", 12, "bold"), command=self.save_logic_chain
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            ctrl_block, text="Load Chain", width=85, height=28, 
            fg_color="#2b2b3d", hover_color="#3a3a52", text_color="#FFFFFF",
            font=("Arial", 12, "bold"), command=self.load_logic_chain
        ).pack(side="left", padx=3)

    # =======================================================
    # UI COMPONENT: MAIN COLUMNS
    # =======================================================
    def create_main_layout(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=12, pady=6)

        # --- LEFT COLUMN (Detector Creation & Rule Manager) ---
        left_col = ctk.CTkFrame(self.main_container, width=490, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=False, padx=(0, 6))
        left_col.pack_propagate(False)

        # Tabs System inside Left Column
        self.tabview = ctk.CTkTabview(left_col, width=480, height=650, fg_color=self.color_bg_card, segmented_button_selected_color=self.color_accent, segmented_button_selected_hover_color="#00D2FF", text_color="white")
        self.tabview.pack(fill="both", expand=True)
        self.tab_capture = self.tabview.add("1. Create Detectors")
        self.tab_logic = self.tabview.add("2. Rule Sequencing")
        
        # Setup content for each tab
        self.setup_capture_tab()
        self.setup_logic_tab()

        # --- RIGHT COLUMN (Action Sequences & Rule Customization) ---
        right_col = ctk.CTkFrame(self.main_container, fg_color=self.color_bg_card, border_color=self.color_border, border_width=1)
        right_col.pack(side="left", fill="both", expand=True, padx=(6, 0))

        # Main header inside the editor container
        self.editor_title_frame = ctk.CTkFrame(right_col, height=45, fg_color="transparent")
        self.editor_title_frame.pack(fill="x", padx=15, pady=(15, 0))
        self.editor_title_frame.pack_propagate(False)
        
        self.editor_label = ctk.CTkLabel(
            self.editor_title_frame, text="Rule Sequence Editor", 
            font=("Arial", 16, "bold"), text_color=self.color_accent
        )
        self.editor_label.pack(side="left")

        # 1. Placeholder when no rule is selected
        self.placeholder_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        self.placeholder_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            self.placeholder_frame, text="No Rule Selected", 
            font=("Arial", 18, "bold"), text_color=self.color_text_muted
        ).pack(expand=True, pady=(100, 5))
        
        ctk.CTkLabel(
            self.placeholder_frame, 
            text="Select a rule from the 'Rule Sequencing' tab\nto customize actions and parameters.", 
            font=("Arial", 12), text_color=self.color_text_muted, justify="center"
        ).pack(expand=True, pady=(0, 150))

        # 2. Real editor container (initially hidden)
        self.editor_container = ctk.CTkFrame(right_col, fg_color="transparent")
        # Managed dynamically inside select_rule()

        # Rule Metadata/Parameters card
        self.frame_editor_params = ctk.CTkFrame(self.editor_container, fg_color="#181822", border_color=self.color_border, border_width=1)
        self.frame_editor_params.pack(fill="x", padx=15, pady=10)

        # Action Builder Card
        self.action_builder_card = ctk.CTkFrame(self.editor_container, fg_color="#181822", border_color=self.color_border, border_width=1)
        self.action_builder_card.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(self.action_builder_card, text="ADD TRIGGERED ACTION", font=("Arial", 12, "bold"), text_color=self.color_accent).pack(anchor="w", padx=15, pady=(10, 5))
        
        action_selector_row = ctk.CTkFrame(self.action_builder_card, fg_color="transparent")
        action_selector_row.pack(fill="x", padx=15, pady=5)
        
        self.action_type = ctk.CTkOptionMenu(
            action_selector_row, 
            values=["Press Key", "Key Down (Hold)", "Key Up (Release)", "Type Text", "Wait (ms)", "Click Found Spot", "Click Custom (X,Y)", "Mouse Scroll", "Drag and Drop"],
            width=180, fg_color="#2b2b3d", button_color="#3a3a52", button_hover_color="#4d4d6a",
            command=self.on_action_type_change
        )
        self.action_type.pack(side="left", padx=(0, 10))

        # Sub-frames for dynamic input fields depending on action type
        self.action_input_frame = ctk.CTkFrame(self.action_builder_card, fg_color="transparent")
        self.action_input_frame.pack(fill="x", padx=15, pady=5)

        # Frame A: Press Key Input
        self.frame_action_key = ctk.CTkFrame(self.action_input_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_action_key, text="Key:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(0, 5))
        self.entry_act_key = ctk.CTkEntry(self.frame_action_key, placeholder_text="e.g. space, f5, a", width=160, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_key.pack(side="left")

        # Frame B: Type Text Input
        self.frame_action_text = ctk.CTkFrame(self.action_input_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_action_text, text="Text:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(0, 5))
        self.entry_act_text = ctk.CTkEntry(self.frame_action_text, placeholder_text="Enter text to type...", width=220, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_text.pack(side="left")

        # Frame C: Wait Milliseconds Input
        self.frame_action_wait = ctk.CTkFrame(self.action_input_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_action_wait, text="Duration (ms):", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(0, 5))
        self.entry_act_wait = ctk.CTkEntry(self.frame_action_wait, placeholder_text="e.g. 500", width=120, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_wait.pack(side="left")

        # Frame D: Click Found Spot Click Type
        self.frame_action_click_found = ctk.CTkFrame(self.action_input_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_action_click_found, text="Click Type:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(0, 5))
        self.menu_act_click_found = ctk.CTkOptionMenu(self.frame_action_click_found, values=["Left Click", "Right Click", "Double Click"], fg_color="#2b2b3d", button_color="#3a3a52", width=140)
        self.menu_act_click_found.pack(side="left")

        # Frame E: Click Custom Coord Input
        self.frame_action_click_custom = ctk.CTkFrame(self.action_input_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_action_click_custom, text="Coords:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(0, 5))
        self.entry_act_cx = ctk.CTkEntry(self.frame_action_click_custom, placeholder_text="X", width=55, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_cx.pack(side="left", padx=2)
        self.entry_act_cy = ctk.CTkEntry(self.frame_action_click_custom, placeholder_text="Y", width=55, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_cy.pack(side="left", padx=2)
        
        ctk.CTkButton(
            self.frame_action_click_custom, text="Pick Spot", width=75, height=28,
            fg_color="#2b2b3d", hover_color="#3a3a52", font=("Arial", 11, "bold"),
            command=lambda: self.start_overlay("coord")
        ).pack(side="left", padx=6)
        
        ctk.CTkLabel(self.frame_action_click_custom, text="Click:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(5, 5))
        self.menu_act_click_custom = ctk.CTkOptionMenu(self.frame_action_click_custom, values=["Left Click", "Right Click", "Double Click"], fg_color="#2b2b3d", button_color="#3a3a52", width=120)
        self.menu_act_click_custom.pack(side="left")

        # Frame F: Mouse Scroll Input
        self.frame_action_scroll = ctk.CTkFrame(self.action_input_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_action_scroll, text="Scroll Amount:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(0, 5))
        self.entry_act_scroll = ctk.CTkEntry(self.frame_action_scroll, placeholder_text="e.g. 100 or -100", width=150, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_scroll.pack(side="left")

        # Frame G: Drag and Drop Input
        self.frame_action_drag = ctk.CTkFrame(self.action_input_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_action_drag, text="From X,Y:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(2, 2))
        self.entry_act_drag_x1 = ctk.CTkEntry(self.frame_action_drag, placeholder_text="X1", width=40, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_drag_x1.pack(side="left", padx=1)
        self.entry_act_drag_y1 = ctk.CTkEntry(self.frame_action_drag, placeholder_text="Y1", width=40, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_drag_y1.pack(side="left", padx=1)
        
        ctk.CTkButton(
            self.frame_action_drag, text="Pick A", width=45, height=26,
            fg_color="#2b2b3d", hover_color="#3a3a52", font=("Arial", 10, "bold"),
            command=lambda: self.start_overlay("drag_start")
        ).pack(side="left", padx=3)
        
        ctk.CTkLabel(self.frame_action_drag, text="To X,Y:", font=("Arial", 12), text_color="#FFFFFF").pack(side="left", padx=(2, 2))
        self.entry_act_drag_x2 = ctk.CTkEntry(self.frame_action_drag, placeholder_text="X2", width=40, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_drag_x2.pack(side="left", padx=1)
        self.entry_act_drag_y2 = ctk.CTkEntry(self.frame_action_drag, placeholder_text="Y2", width=40, fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_act_drag_y2.pack(side="left", padx=1)
        
        ctk.CTkButton(
            self.frame_action_drag, text="Pick B", width=45, height=26,
            fg_color="#2b2b3d", hover_color="#3a3a52", font=("Arial", 10, "bold"),
            command=lambda: self.start_overlay("drag_end")
        ).pack(side="left", padx=3)

        # Bottom Button for Action Builder
        action_btn_row = ctk.CTkFrame(self.action_builder_card, fg_color="transparent")
        action_btn_row.pack(fill="x", padx=15, pady=(5, 10))
        
        ctk.CTkButton(
            action_btn_row, text="+ Add Action to Sequence", width=180, height=32, 
            fg_color=self.color_success, hover_color="#00C853", text_color="#121214",
            font=("Arial", 12, "bold"), command=self.add_action_to_rule
        ).pack(side="right")

        # Initial input visibility setup
        self.on_action_type_change("Press Key")

        # Action Sequence Card
        self.action_sequence_card = ctk.CTkFrame(self.editor_container, fg_color="#181822", border_color=self.color_border, border_width=1)
        self.action_sequence_card.pack(fill="both", expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(self.action_sequence_card, text="EXECUTED ACTION SEQUENCE", font=("Arial", 12, "bold"), text_color=self.color_accent).pack(anchor="w", padx=15, pady=(10, 5))

        self.action_scroll = ctk.CTkScrollableFrame(self.action_sequence_card, fg_color="#0b0b0f")
        self.action_scroll.pack(fill="both", expand=True, padx=15, pady=10)

        # Engine controls at the bottom of the column
        engine_ctrl_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        engine_ctrl_frame.pack(fill="x", padx=15, pady=15)
        
        self.start_btn = ctk.CTkButton(
            engine_ctrl_frame, text="START ENGINE", width=220, height=44, 
            fg_color=self.color_success, hover_color="#00C853", text_color="#121214",
            font=("Arial", 14, "bold"), command=self.start_automation
        )
        self.start_btn.pack(side="left", padx=(0, 10))
        
        self.stop_btn = ctk.CTkButton(
            engine_ctrl_frame, text="STOP BOT", width=220, height=44, 
            fg_color=self.color_danger, hover_color="#D50000", text_color="#FFFFFF",
            font=("Arial", 14, "bold"), state="disabled", command=self.stop_automation
        )
        self.stop_btn.pack(side="left")

    # =======================================================
    # TAB 1: CAPTURE INGREDIENTS
    # =======================================================
    def setup_capture_tab(self):
        cap_scroll = ctk.CTkScrollableFrame(self.tab_capture, fg_color="transparent")
        cap_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Card A: Pixel Detector Setup
        pixel_card = ctk.CTkFrame(cap_scroll, fg_color="#181822", border_color=self.color_border, border_width=1)
        pixel_card.pack(fill="x", pady=5)
        
        ctk.CTkLabel(pixel_card, text="Option A: Pixel Color Detector", font=("Arial", 13, "bold"), text_color=self.color_accent).pack(anchor="w", padx=15, pady=(10, 5))

        # Fields row
        fields_row = ctk.CTkFrame(pixel_card, fg_color="transparent")
        fields_row.pack(fill="x", padx=15, pady=5)

        # Coord X
        col_x = ctk.CTkFrame(fields_row, fg_color="transparent")
        col_x.pack(side="left", expand=True, fill="x", padx=2)
        ctk.CTkLabel(col_x, text="X:", font=("Arial", 11), text_color=self.color_text_muted).pack(anchor="w")
        self.entry_X = ctk.CTkEntry(col_x, placeholder_text="X Coord", fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_X.pack(fill="x")

        # Coord Y
        col_y = ctk.CTkFrame(fields_row, fg_color="transparent")
        col_y.pack(side="left", expand=True, fill="x", padx=2)
        ctk.CTkLabel(col_y, text="Y:", font=("Arial", 11), text_color=self.color_text_muted).pack(anchor="w")
        self.entry_Y = ctk.CTkEntry(col_y, placeholder_text="Y Coord", fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_Y.pack(fill="x")

        # RGB
        col_rgb = ctk.CTkFrame(fields_row, fg_color="transparent")
        col_rgb.pack(side="left", expand=True, fill="x", padx=2)
        ctk.CTkLabel(col_rgb, text="RGB:", font=("Arial", 11), text_color=self.color_text_muted).pack(anchor="w")
        self.entry_RGB = ctk.CTkEntry(col_rgb, placeholder_text="R,G,B", fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_RGB.pack(fill="x")
        self.entry_RGB.bind("<KeyRelease>", lambda e: self.update_pixel_preview())

        # Buttons/Preview row
        btn_preview_row = ctk.CTkFrame(pixel_card, fg_color="transparent")
        btn_preview_row.pack(fill="x", padx=15, pady=10)

        ctk.CTkButton(
            btn_preview_row, text="Pick Pixel", width=110, height=28,
            fg_color="#2b2b3d", hover_color="#3a3a52", border_color=self.color_accent, border_width=1,
            font=("Arial", 11, "bold"), command=lambda: self.start_overlay("pixel")
        ).pack(side="left")

        # Visual color swatch preview
        ctk.CTkLabel(btn_preview_row, text="Swatch:", font=("Arial", 11), text_color=self.color_text_muted).pack(side="left", padx=(20, 5))
        self.pixel_swatch = ctk.CTkFrame(btn_preview_row, width=30, height=18, corner_radius=3, fg_color="#2b2b2b")
        self.pixel_swatch.pack(side="left", pady=5)

        # Tolerance slider inside Detector Tab
        tol_row = ctk.CTkFrame(pixel_card, fg_color="transparent")
        tol_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.lbl_tolerance_val = ctk.CTkLabel(tol_row, text="Tolerance: 20", font=("Arial", 11), text_color="#FFFFFF", width=100, anchor="w")
        self.lbl_tolerance_val.pack(side="left")
        
        self.slider_tolerance = ctk.CTkSlider(tol_row, from_=0, to=100, number_of_steps=100, progress_color=self.color_accent, command=self.on_tolerance_slider)
        self.slider_tolerance.set(20)
        self.slider_tolerance.pack(side="left", fill="x", expand=True, padx=5)

        # Pixel search options row / Invert Match
        pixel_opts_row = ctk.CTkFrame(pixel_card, fg_color="transparent")
        pixel_opts_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.checkbox_pixel_invert = ctk.CTkCheckBox(
            pixel_opts_row, text="Invert Match (Trigger when color is ABSENT / NOT matched)", 
            font=("Arial", 11), text_color="#FFFFFF",
            fg_color=self.color_accent, hover_color="#00D2FF"
        )
        self.checkbox_pixel_invert.pack(side="left")

        # Card B: Image Detector Setup
        image_card = ctk.CTkFrame(cap_scroll, fg_color="#181822", border_color=self.color_border, border_width=1)
        image_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(image_card, text="Option B: Image Template Detector", font=("Arial", 13, "bold"), text_color=self.color_accent).pack(anchor="w", padx=15, pady=(10, 5))

        # Path row
        path_row = ctk.CTkFrame(image_card, fg_color="transparent")
        path_row.pack(fill="x", padx=15, pady=5)
        
        self.entry_Image = ctk.CTkEntry(path_row, placeholder_text="Path to image template...", fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_Image.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_Image.bind("<KeyRelease>", lambda e: self.update_image_preview())
        
        ctk.CTkButton(
            path_row, text="Capture Region", width=120, height=28,
            fg_color="#2b2b3d", hover_color="#3a3a52", border_color=self.color_accent, border_width=1,
            font=("Arial", 11, "bold"), command=lambda: self.start_overlay("image")
        ).pack(side="right")

        # Preview and parameters row
        img_preview_row = ctk.CTkFrame(image_card, fg_color="transparent")
        img_preview_row.pack(fill="x", padx=15, pady=(5, 10))

        # Thumbnail Label
        ctk.CTkLabel(img_preview_row, text="Preview:", font=("Arial", 11), text_color=self.color_text_muted).pack(side="left", padx=(0, 5))
        self.lbl_image_preview = ctk.CTkLabel(img_preview_row, text="No Image Selected", font=("Arial", 10, "italic"), text_color=self.color_text_muted, fg_color="#0b0b0f", width=100, height=45, corner_radius=4)
        self.lbl_image_preview.pack(side="left")

        # Confidence Slider
        slider_col = ctk.CTkFrame(img_preview_row, fg_color="transparent")
        slider_col.pack(side="left", fill="x", expand=True, padx=(20, 0))
        
        self.lbl_confidence_val = ctk.CTkLabel(slider_col, text="Confidence: 0.80", font=("Arial", 11), text_color="#FFFFFF", anchor="w")
        self.lbl_confidence_val.pack(anchor="w")
        
        self.slider_confidence = ctk.CTkSlider(slider_col, from_=0.5, to=1.0, number_of_steps=50, progress_color=self.color_accent, command=self.on_confidence_slider)
        self.slider_confidence.set(0.80)
        self.slider_confidence.pack(fill="x")

        # Image search options row
        img_opts_row = ctk.CTkFrame(image_card, fg_color="transparent")
        img_opts_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.checkbox_full_screen = ctk.CTkCheckBox(
            img_opts_row, text="Full Screen Search (slower, scans entire desktop)", 
            font=("Arial", 11), text_color="#FFFFFF",
            fg_color=self.color_accent, hover_color="#00D2FF"
        )
        self.checkbox_full_screen.pack(side="left")

        self.checkbox_image_invert = ctk.CTkCheckBox(
            img_opts_row, text="Invert Match (Trigger when image is ABSENT)", 
            font=("Arial", 11), text_color="#FFFFFF",
            fg_color=self.color_accent, hover_color="#00D2FF"
        )
        self.checkbox_image_invert.pack(side="left", padx=(20, 0))

        # Card C: Saving Profile Registry
        save_card = ctk.CTkFrame(cap_scroll, fg_color="#181822", border_color=self.color_border, border_width=1)
        save_card.pack(fill="x", pady=5)
        
        ctk.CTkLabel(save_card, text="Save Detector Profile", font=("Arial", 13, "bold"), text_color="#FFFFFF").pack(anchor="w", padx=15, pady=(10, 5))
        
        save_fields_row = ctk.CTkFrame(save_card, fg_color="transparent")
        save_fields_row.pack(fill="x", padx=15, pady=(5, 10))
        
        self.entry_Name = ctk.CTkEntry(save_fields_row, placeholder_text="e.g. play_button_ready", fg_color="#0b0b0f", border_color=self.color_border)
        self.entry_Name.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.save_btn = ctk.CTkButton(
            save_fields_row, text="SAVE DETECTOR (.json)", width=170, height=32,
            fg_color=self.color_success, hover_color="#00C853", text_color="#121214",
            font=("Arial", 12, "bold"), command=self.save_new_profile
        )
        self.save_btn.pack(side="right")
        
        self.save_status = ctk.CTkLabel(save_card, text="", font=("Arial", 11), text_color=self.color_success)
        self.save_status.pack(pady=(0, 10))

    # =======================================================
    # TAB 2: LOGIC RULE SEQUENCING
    # =======================================================
    def setup_logic_tab(self):
        self.logic_frame = ctk.CTkFrame(self.tab_logic, fg_color="transparent")
        self.logic_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Profile selection card
        sel_card = ctk.CTkFrame(self.logic_frame, fg_color="#181822", border_color=self.color_border, border_width=1)
        sel_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(sel_card, text="Available Profiles:", font=("Arial", 12, "bold"), text_color=self.color_accent).pack(anchor="w", padx=15, pady=(10, 2))
        
        row_dropdown = ctk.CTkFrame(sel_card, fg_color="transparent")
        row_dropdown.pack(fill="x", padx=15, pady=(5, 10))
        
        self.profile_dropdown = ctk.CTkOptionMenu(row_dropdown, values=["No Profiles"], fg_color="#2b2b3d", button_color="#3a3a52", button_hover_color="#4d4d6a")
        self.profile_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        ctk.CTkButton(
            row_dropdown, text="↻ Refresh", width=90, height=28,
            fg_color="#2b2b3d", hover_color="#3a3a52", font=("Arial", 11),
            command=self.refresh_profiles
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            row_dropdown, text="+ Add to Chain", width=120, height=28,
            fg_color=self.color_success, hover_color="#00C853", text_color="#121214",
            font=("Arial", 11, "bold"), command=self.add_rule_to_list
        ).pack(side="left", padx=3)

        # Active rules list frame
        list_card = ctk.CTkFrame(self.logic_frame, fg_color="#181822", border_color=self.color_border, border_width=1)
        list_card.pack(fill="both", expand=True)

        ctk.CTkLabel(list_card, text="Active Logic Sequence Chain:", font=("Arial", 12, "bold"), text_color="#FFFFFF").pack(anchor="w", padx=15, pady=(10, 5))
        
        self.rule_scroll = ctk.CTkScrollableFrame(list_card, fg_color="#0b0b0f")
        self.rule_scroll.pack(fill="both", expand=True, padx=15, pady=(5, 15))

    # =======================================================
    # UI COMPONENT: SYSTEM LOG CONSOLE
    # =======================================================
    def create_log_console(self):
        log_frame = ctk.CTkFrame(self, height=160, fg_color=self.color_bg_card, border_color=self.color_border, border_width=1)
        log_frame.pack(fill="x", padx=12, pady=(6, 12))
        log_frame.pack_propagate(False)

        # Log Header
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=(5, 0))
        
        ctk.CTkLabel(log_header, text="LIVE SYSTEM LOG / CONSOLE", font=("Arial", 11, "bold"), text_color=self.color_accent).pack(side="left")
        
        ctk.CTkButton(
            log_header, text="Clear Console", width=90, height=20,
            fg_color="transparent", hover_color="#2b2b3d", text_color=self.color_accent,
            font=("Arial", 10), command=self.clear_console
        ).pack(side="right")

        # Scrolling textbox acting as console
        self.log_textbox = ctk.CTkTextbox(
            log_frame, fg_color="#07070a", border_color=self.color_border, border_width=1,
            text_color="#A0A0A5", font=("Courier New", 12)
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(5, 10))
        self.log_textbox.configure(state="disabled")

    # =======================================================
    # CORE INTERACTION LOGIC
    # =======================================================
    def on_action_type_change(self, selected_type):
        # Hide all inputs
        self.frame_action_key.pack_forget()
        self.frame_action_text.pack_forget()
        self.frame_action_wait.pack_forget()
        self.frame_action_click_found.pack_forget()
        self.frame_action_click_custom.pack_forget()
        self.frame_action_scroll.pack_forget()
        self.frame_action_drag.pack_forget()

        # Show matching input
        if selected_type in ["Press Key", "Key Down (Hold)", "Key Up (Release)"]:
            self.frame_action_key.pack(side="left", padx=5)
        elif selected_type == "Type Text":
            self.frame_action_text.pack(side="left", padx=5)
        elif selected_type == "Wait (ms)":
            self.frame_action_wait.pack(side="left", padx=5)
        elif selected_type == "Click Found Spot":
            self.frame_action_click_found.pack(side="left", padx=5)
        elif selected_type == "Click Custom (X,Y)":
            self.frame_action_click_custom.pack(side="left", padx=5)
        elif selected_type == "Mouse Scroll":
            self.frame_action_scroll.pack(side="left", padx=5)
        elif selected_type == "Drag and Drop":
            self.frame_action_drag.pack(side="left", padx=5)

    def on_loop_speed_change(self, val):
        val = int(float(val))
        self.lbl_loop_speed.configure(text=f"Loop Delay: {val}ms")

    def on_tolerance_slider(self, val):
        val = int(float(val))
        self.lbl_tolerance_val.configure(text=f"Tolerance: {val}")

    def on_confidence_slider(self, val):
        val = round(float(val), 2)
        self.lbl_confidence_val.configure(text=f"Confidence: {val:.2f}")

    def on_editor_tolerance_slider(self, val):
        if self.selected_rule_index is None: return
        val = int(float(val))
        self.active_rules[self.selected_rule_index]["tolerance"] = val
        self.lbl_editor_param_val.configure(text=f"Match Tolerance: {val}")

    def on_editor_confidence_slider(self, val):
        if self.selected_rule_index is None: return
        val = round(float(val), 2)
        self.active_rules[self.selected_rule_index]["confidence"] = val
        self.lbl_editor_param_val.configure(text=f"Match Confidence: {val:.2f}")

    def on_editor_fullscreen_toggle(self, is_fs):
        if self.selected_rule_index is None: return
        self.active_rules[self.selected_rule_index]["full_screen"] = is_fs

    def on_editor_invert_toggle(self, is_inv):
        if self.selected_rule_index is None: return
        self.active_rules[self.selected_rule_index]["invert_match"] = is_inv

    def show_flash_highlight(self, x, y, width=40, height=40):
        # Create a tiny borderless green flashing square on screen
        highlight = ctk.CTkToplevel(self)
        highlight.attributes("-topmost", True)
        highlight.overrideredirect(True)
        # Position it centered around (x, y)
        hx = int(x - width/2)
        hy = int(y - height/2)
        highlight.geometry(f"{width}x{height}+{hx}+{hy}")
        
        # Transparent center with a thick neon green border
        canvas = ctk.CTkCanvas(highlight, width=width, height=height, bg="white", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        # Make the background color transparent
        highlight.config(bg="green")
        highlight.attributes("-transparentcolor", "white")
        
        canvas.create_rectangle(2, 2, width-2, height-2, outline=self.color_success, width=4)
        
        # Flash / destroy after 1.5 seconds
        def destroy_highlight():
            try: highlight.destroy()
            except: pass
            
        self.after(1500, destroy_highlight)

    def test_selected_detector(self):
        if self.selected_rule_index is None: return
        rule = self.active_rules[self.selected_rule_index]
        
        self.log_message("Starting diagnostics test for selected detector...", "INFO")
        
        # Hide main window briefly to let the test capture the actual screen
        self.withdraw()
        self.after(250, lambda: self._run_detector_diagnostics(rule))

    def _run_detector_diagnostics(self, rule):
        data = rule["data"]
        found = False
        found_x, found_y = 0, 0
        w, h = 40, 40
        log_type = "INFO"
        log_msg = ""
        
        try:
            with mss.mss() as sct:
                # --- PIXEL TYPE ---
                if data.get("type") == "pixel":
                    px_x = int(data["x"])
                    px_y = int(data["y"])
                    monitor = {"top": px_y, "left": px_x, "width": 1, "height": 1}
                    img = sct.grab(monitor)
                    pixel = img.pixel(0, 0)
                    
                    target = list(map(int, data["rgb"].split(',')))
                    tolerance = rule.get("tolerance", data.get("tolerance", 20))
                    
                    diff = math.sqrt(sum((a - b) ** 2 for a, b in zip(pixel, target)))
                    
                    curr_hex = "#{:02x}{:02x}{:02x}".format(*pixel)
                    target_hex = "#{:02x}{:02x}{:02x}".format(*target)
                    
                    is_invert = rule.get("invert_match", data.get("invert_match", False))
                    base_found = diff < tolerance
                    found = not base_found if is_invert else base_found
                    
                    found_x, found_y = px_x, px_y
                    
                    if found:
                        log_type = "SUCCESS"
                        if is_invert:
                            log_msg = f"Diagnostics: SUCCESS (Inverted)! Color {curr_hex} differs from target {target_hex} (diff: {diff:.1f} >= tolerance {tolerance})."
                        else:
                            log_msg = f"Diagnostics: SUCCESS! Color matched {curr_hex} (diff: {diff:.1f} < tolerance {tolerance})."
                    else:
                        log_type = "WARNING"
                        if is_invert:
                            log_msg = f"Diagnostics: FAILED (Inverted)! Color {curr_hex} is too close to target {target_hex} (diff: {diff:.1f} < tolerance {tolerance})."
                        else:
                            log_msg = f"Diagnostics: FAILED! Color is {curr_hex}, expected target {target_hex} (diff: {diff:.1f} >= tolerance {tolerance})."
                
                # --- IMAGE TYPE ---
                elif data.get("type") == "image":
                    path = data["image_path"]
                    template = cv2.imread(path, 0)
                    if template is not None:
                        th, tw = template.shape
                        w, h = tw, th
                        
                        is_fs = rule.get("full_screen", data.get("full_screen", False))
                        region = data.get("region")
                        
                        if not is_fs and region:
                            rx1, ry1, rx2, ry2 = region
                            pad = 10
                            primary = sct.monitors[1]
                            px1 = max(primary["left"], rx1 - pad)
                            py1 = max(primary["top"], ry1 - pad)
                            px2 = min(primary["left"] + primary["width"], rx2 + pad)
                            py2 = min(primary["top"] + primary["height"], ry2 + pad)
                            
                            monitor = {
                                "left": int(px1),
                                "top": int(py1),
                                "width": int(px2 - px1),
                                "height": int(py2 - py1)
                            }
                            if monitor["width"] < tw or monitor["height"] < th:
                                monitor = sct.monitors[1]
                        else:
                            monitor = sct.monitors[1]
                            
                        sct_img = np.array(sct.grab(monitor))
                        gray_screen = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2GRAY)
                        res = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
                        
                        confidence = rule.get("confidence", data.get("confidence", 0.8))
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                        
                        is_invert = rule.get("invert_match", data.get("invert_match", False))
                        base_found = max_val >= confidence
                        found = not base_found if is_invert else base_found
                        
                        if base_found:
                            found_x = int(monitor["left"] + max_loc[0] + tw/2)
                            found_y = int(monitor["top"] + max_loc[1] + th/2)
                        else:
                            if is_invert:
                                if region:
                                    found_x = int((region[0] + region[2])/2)
                                    found_y = int((region[1] + region[3])/2)
                                else:
                                    found_x = int(monitor["left"] + monitor["width"]/2)
                                    found_y = int(monitor["top"] + monitor["height"]/2)
                            
                        if found:
                            log_type = "SUCCESS"
                            if is_invert:
                                log_msg = f"Diagnostics: SUCCESS (Inverted)! Image is ABSENT on screen (highest confidence {max_val:.2f} < target {confidence:.2f})."
                            else:
                                log_msg = f"Diagnostics: SUCCESS! Image FOUND with confidence {max_val:.2f} (target {confidence:.2f}) at screen center ({found_x}, {found_y})."
                        else:
                            log_type = "WARNING"
                            if is_invert:
                                log_msg = f"Diagnostics: FAILED (Inverted)! Image is PRESENT on screen (highest confidence {max_val:.2f} >= target {confidence:.2f})."
                            else:
                                log_msg = f"Diagnostics: FAILED! Image not found. Highest match confidence was {max_val:.2f} (target {confidence:.2f})."
                    else:
                        log_type = "ERROR"
                        log_msg = f"Diagnostics: Could not load template file '{path}'"
        except Exception as e:
            log_type = "ERROR"
            log_msg = f"Diagnostics: Error during screen check: {e}"
            
        # Restore window
        self.deiconify()
        self.log_message(log_msg, log_type)
        
        # Draw the neon green flashing visual feedback overlay if successful!
        if found and (log_type == "SUCCESS"):
            self.show_flash_highlight(found_x, found_y, w, h)

    def toggle_always_on_top(self):
        state = self.switch_always_on_top.get()
        self.attributes("-topmost", state)
        self.log_message(f"Always on Top: {'Enabled' if state else 'Disabled'}")

    def clear_console(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def log_message(self, message, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{level}] {message}\n"
        self.after(0, self._append_log, formatted_msg, level)
        print(f"[{timestamp}] [{level}] {message}")

    def _append_log(self, text, level):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", text)
        
        # Color coding text logs
        text_widget = self.log_textbox._textbox
        if "INFO" not in text_widget.tag_names():
            text_widget.tag_config("INFO", foreground="#8a8a9e")
            text_widget.tag_config("SUCCESS", foreground=self.color_success)
            text_widget.tag_config("WARNING", foreground="#FFD700")
            text_widget.tag_config("ERROR", foreground=self.color_danger)
            text_widget.tag_config("ENGINE", foreground=self.color_accent)
            
        last_line_index = float(text_widget.index("end-1c"))
        start_index = f"{int(last_line_index - 1)}.0"
        end_index = f"{int(last_line_index)}.0"
        text_widget.tag_add(level, start_index, end_index)
        
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    # =======================================================
    # VISUAL REAL-TIME COMPONENT PREVIEWS
    # =======================================================
    def update_pixel_preview(self):
        rgb_str = self.entry_RGB.get().strip()
        try:
            rgb = [int(c.strip()) for c in rgb_str.split(",")]
            if len(rgb) == 3 and all(0 <= c <= 255 for c in rgb):
                hex_color = "#{:02x}{:02x}{:02x}".format(*rgb)
                self.pixel_swatch.configure(fg_color=hex_color)
                return
        except:
            pass
        self.pixel_swatch.configure(fg_color="#2b2b2b")

    def update_image_preview(self):
        img_path = self.entry_Image.get().strip()
        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((70, 35))
                self.preview_photo = ImageTk.PhotoImage(img)
                self.lbl_image_preview.configure(image=self.preview_photo, text="")
            except:
                self.lbl_image_preview.configure(image="", text="Preview Error")
        else:
            self.lbl_image_preview.configure(image="", text="No Image Selected")

    # =======================================================
    # LOGIC: MANAGING RULES
    # =======================================================
    def refresh_profiles(self):
        files = glob.glob("*.json")
        # Filter files to make sure they are not logic chain files
        valid_profiles = []
        for file in files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    # Simple detector profile signature check
                    if isinstance(data, dict) and "type" in data:
                        valid_profiles.append(file)
            except:
                pass
                
        if valid_profiles:
            self.profile_dropdown.configure(values=valid_profiles)
            self.profile_dropdown.set(valid_profiles[0])
        else:
            self.profile_dropdown.configure(values=["No Profiles"])
            self.profile_dropdown.set("No Profiles")

    def add_rule_to_list(self):
        filename = self.profile_dropdown.get()
        if filename == "No Profiles": 
            self.log_message("Please create a detector profile first!", "WARNING")
            return

        try:
            with open(filename, "r") as f:
                data = json.load(f)
            
            new_rule = {
                "name": filename,
                "data": data, 
                "actions": [],
                "tolerance": data.get("tolerance", 20),
                "confidence": data.get("confidence", 0.8),
                "full_screen": data.get("full_screen", False),
                "invert_match": data.get("invert_match", False)
            }
            self.active_rules.append(new_rule)
            self.log_message(f"Rule '{filename}' added to sequencing chain.", "SUCCESS")
            self.render_rule_list()
            self.select_rule(len(self.active_rules) - 1)
        except Exception as e:
            self.log_message(f"Error loading rule: {e}", "ERROR")

    def render_rule_list(self):
        for widget in self.rule_scroll.winfo_children():
            widget.destroy()

        for index, rule in enumerate(self.active_rules):
            row = ctk.CTkFrame(self.rule_scroll, fg_color="#181824" if self.selected_rule_index == index else "#111116", border_width=1, border_color=self.color_accent if self.selected_rule_index == index else self.color_border)
            row.pack(fill="x", pady=4, padx=5)
            
            btn_text = f"{index+1}. {os.path.basename(rule['name'])}"
            rule_type = rule['data'].get('type')

            # Render mini previews inside the sequence list
            swatch_container = ctk.CTkFrame(row, width=20, height=20, fg_color="transparent")
            swatch_container.pack(side="left", padx=5)
            
            if rule_type == 'pixel':
                btn_text += " (PXL)"
                rgb_str = rule['data'].get('rgb', '255,255,255')
                try:
                    rgb = [int(c.strip()) for c in rgb_str.split(",")]
                    hex_color = "#{:02x}{:02x}{:02x}".format(*rgb)
                except:
                    hex_color = "#FFFFFF"
                
                mini_preview = ctk.CTkFrame(swatch_container, width=12, height=12, corner_radius=3, fg_color=hex_color)
                mini_preview.pack(pady=4)
            else:
                btn_text += " (IMG)"
                mini_preview = ctk.CTkFrame(swatch_container, width=12, height=12, corner_radius=3, fg_color=self.color_accent)
                mini_preview.pack(pady=4)

            cmd = lambda i=index: self.select_rule(i)
            ctk.CTkButton(
                row, text=btn_text, anchor="w", fg_color="transparent", 
                text_color=self.color_accent if self.selected_rule_index == index else "#FFFFFF",
                font=("Arial", 12, "bold" if self.selected_rule_index == index else "normal"),
                hover_color="#1c1c28", command=cmd
            ).pack(side="left", fill="x", expand=True)

            del_cmd = lambda i=index: self.delete_rule(i)
            ctk.CTkButton(
                row, text="✕", width=25, height=25, 
                fg_color="transparent", hover_color=self.color_danger, 
                text_color=self.color_danger, font=("Arial", 12, "bold"),
                command=del_cmd
            ).pack(side="right", padx=5)

    def delete_rule(self, index):
        removed = self.active_rules.pop(index)
        self.log_message(f"Removed rule: {os.path.basename(removed['name'])}")
        
        if self.selected_rule_index == index:
            self.selected_rule_index = None
            self.editor_container.pack_forget()
            self.placeholder_frame.pack(fill="both", expand=True)
        elif self.selected_rule_index is not None and self.selected_rule_index > index:
            self.selected_rule_index -= 1
            
        self.render_rule_list()
        self.render_action_list()

    def select_rule(self, index):
        self.selected_rule_index = index
        self.render_rule_list()
        
        # Switch frames
        self.placeholder_frame.pack_forget()
        self.editor_container.pack(fill="both", expand=True)
        
        rule_name = os.path.basename(self.active_rules[index]['name'])
        self.editor_label.configure(text=f"Rule Sequence Editor: {rule_name}")
        
        self.update_editor_params_card()
        self.render_action_list()

    # =======================================================
    # LOGIC: ACTIONS (Added Move Up/Down/Custom coordinates)
    # =======================================================
    def update_editor_params_card(self):
        for widget in self.frame_editor_params.winfo_children():
            widget.destroy()
            
        if self.selected_rule_index is None: return
        
        rule = self.active_rules[self.selected_rule_index]
        rule_type = rule["data"].get("type")
        
        if rule_type == "pixel":
            # Coords details
            coords_lbl = ctk.CTkLabel(self.frame_editor_params, text=f"Type: Pixel Color Detection  |  Coords: ({rule['data'].get('x')}, {rule['data'].get('y')})", font=("Arial", 12), text_color=self.color_text_muted)
            coords_lbl.pack(anchor="w", padx=15, pady=(10, 2))
            
            # Swatch Color Display
            color_sw_row = ctk.CTkFrame(self.frame_editor_params, fg_color="transparent")
            color_sw_row.pack(fill="x", padx=15, pady=2)
            
            ctk.CTkLabel(color_sw_row, text="Target RGB Swatch: ", text_color="#FFFFFF").pack(side="left")
            rgb_str = rule['data'].get('rgb', '255,255,255')
            try:
                rgb = [int(c.strip()) for c in rgb_str.split(",")]
                hex_color = "#{:02x}{:02x}{:02x}".format(*rgb)
            except:
                hex_color = "#FFFFFF"
                
            sh_swatch = ctk.CTkFrame(color_sw_row, width=35, height=18, corner_radius=3, fg_color=hex_color)
            sh_swatch.pack(side="left", padx=5)
            ctk.CTkLabel(color_sw_row, text=f"({rgb_str})", font=("Courier New", 11), text_color=self.color_text_muted).pack(side="left")

            # Invert Match Checkbox for pixel
            inv_row = ctk.CTkFrame(self.frame_editor_params, fg_color="transparent")
            inv_row.pack(fill="x", padx=15, pady=2)
            
            cur_inv = rule.get("invert_match", rule["data"].get("invert_match", False))
            edit_inv_cb = ctk.CTkCheckBox(
                inv_row, text="Invert Match (Trigger when color is ABSENT / NOT matched)", 
                font=("Arial", 11), text_color="#FFFFFF",
                fg_color=self.color_accent, hover_color="#00D2FF",
                command=lambda: self.on_editor_invert_toggle(edit_inv_cb.get() == 1)
            )
            edit_inv_cb.set(1 if cur_inv else 0)
            edit_inv_cb.pack(side="left")

            # Tolerance Slider
            slider_row = ctk.CTkFrame(self.frame_editor_params, fg_color="transparent")
            slider_row.pack(fill="x", padx=15, pady=(5, 10))
            
            cur_tol = rule.get("tolerance", 20)
            self.lbl_editor_param_val = ctk.CTkLabel(slider_row, text=f"Match Tolerance: {cur_tol}", font=("Arial", 12, "bold"), text_color=self.color_accent, width=150, anchor="w")
            self.lbl_editor_param_val.pack(side="left")
            
            edit_tol_slider = ctk.CTkSlider(slider_row, from_=0, to=100, number_of_steps=100, progress_color=self.color_accent, command=self.on_editor_tolerance_slider)
            edit_tol_slider.set(cur_tol)
            edit_tol_slider.pack(side="left", fill="x", expand=True)
            
        else:
            # Image template path
            path_lbl = ctk.CTkLabel(self.frame_editor_params, text=f"Type: Image Template Search  |  Template: {os.path.basename(rule['data'].get('image_path'))}", font=("Arial", 12), text_color=self.color_text_muted)
            path_lbl.pack(anchor="w", padx=15, pady=(10, 2))
            
            # Thumbnail Preview
            img_path = rule['data'].get('image_path')
            if img_path and os.path.exists(img_path):
                try:
                    img_row = ctk.CTkFrame(self.frame_editor_params, fg_color="transparent")
                    img_row.pack(fill="x", padx=15, pady=2)
                    ctk.CTkLabel(img_row, text="Image Preview: ").pack(side="left")
                    
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((70, 35))
                    self.editor_preview_photo = ImageTk.PhotoImage(pil_img)
                    
                    thumb_label = ctk.CTkLabel(img_row, image=self.editor_preview_photo, text="")
                    thumb_label.pack(side="left", padx=5)
                except:
                    pass

            # Full Screen Checkbox inside parameters editor
            fs_row = ctk.CTkFrame(self.frame_editor_params, fg_color="transparent")
            fs_row.pack(fill="x", padx=15, pady=2)
            
            cur_fs = rule.get("full_screen", rule["data"].get("full_screen", False))
            
            edit_fs_cb = ctk.CTkCheckBox(
                fs_row, text="Full Screen Search", 
                font=("Arial", 11), text_color="#FFFFFF",
                fg_color=self.color_accent, hover_color="#00D2FF",
                command=lambda: self.on_editor_fullscreen_toggle(edit_fs_cb.get() == 1)
            )
            edit_fs_cb.set(1 if cur_fs else 0)
            edit_fs_cb.pack(side="left")

            # Invert Match Checkbox inside parameters editor
            cur_inv = rule.get("invert_match", rule["data"].get("invert_match", False))
            edit_inv_cb = ctk.CTkCheckBox(
                fs_row, text="Invert Match (Trigger when ABSENT)", 
                font=("Arial", 11), text_color="#FFFFFF",
                fg_color=self.color_accent, hover_color="#00D2FF",
                command=lambda: self.on_editor_invert_toggle(edit_inv_cb.get() == 1)
            )
            edit_inv_cb.set(1 if cur_inv else 0)
            edit_inv_cb.pack(side="left", padx=(20, 0))

            # Confidence Slider
            slider_row = ctk.CTkFrame(self.frame_editor_params, fg_color="transparent")
            slider_row.pack(fill="x", padx=15, pady=(5, 10))
            
            cur_conf = rule.get("confidence", 0.8)
            self.lbl_editor_param_val = ctk.CTkLabel(slider_row, text=f"Match Confidence: {cur_conf:.2f}", font=("Arial", 12, "bold"), text_color=self.color_accent, width=150, anchor="w")
            self.lbl_editor_param_val.pack(side="left")
            
            edit_conf_slider = ctk.CTkSlider(slider_row, from_=0.5, to=1.0, number_of_steps=50, progress_color=self.color_accent, command=self.on_editor_confidence_slider)
            edit_conf_slider.set(cur_conf)
            edit_conf_slider.pack(side="left", fill="x", expand=True)

        # Unified Diagnostics / Test Match Button at the bottom of parameters editor
        ctk.CTkButton(
            self.frame_editor_params, text="🔍 Test Detector Match", height=32,
            fg_color="#2b2b3d", hover_color="#3a3a52", border_color=self.color_accent, border_width=1,
            text_color=self.color_accent, font=("Arial", 12, "bold"), 
            command=self.test_selected_detector
        ).pack(fill="x", padx=15, pady=(5, 10))

    def add_action_to_rule(self):
        if self.selected_rule_index is None: return

        atype = self.action_type.get()
        aval = ""
        
        if atype in ["Press Key", "Key Down (Hold)", "Key Up (Release)"]:
            aval = self.entry_act_key.get().strip()
            if not aval:
                self.log_message("Please specify a keyboard key!", "WARNING")
                return
        elif atype == "Type Text":
            aval = self.entry_act_text.get().strip()
            if not aval:
                self.log_message("Please fill out the text to type!", "WARNING")
                return
        elif atype == "Wait (ms)":
            aval = self.entry_act_wait.get().strip()
            if not aval:
                self.log_message("Please fill out wait duration in ms!", "WARNING")
                return
            try:
                int(aval)
            except ValueError:
                self.log_message("Wait duration must be a valid integer!", "WARNING")
                return
        elif atype == "Click Found Spot":
            aval = self.menu_act_click_found.get()
        elif atype == "Click Custom (X,Y)":
            cx = self.entry_act_cx.get().strip()
            cy = self.entry_act_cy.get().strip()
            ctype = self.menu_act_click_custom.get()
            if not cx or not cy:
                self.log_message("Coordinates X and Y must be filled!", "WARNING")
                return
            try:
                int(cx)
                int(cy)
            except ValueError:
                self.log_message("Coordinates must be valid integers!", "WARNING")
                return
            aval = f"{cx},{cy},{ctype}"
        elif atype == "Mouse Scroll":
            aval = self.entry_act_scroll.get().strip()
            if not aval:
                self.log_message("Please specify scroll amount!", "WARNING")
                return
            try:
                int(aval)
            except ValueError:
                self.log_message("Scroll amount must be a valid integer!", "WARNING")
                return
        elif atype == "Drag and Drop":
            x1 = self.entry_act_drag_x1.get().strip()
            y1 = self.entry_act_drag_y1.get().strip()
            x2 = self.entry_act_drag_x2.get().strip()
            y2 = self.entry_act_drag_y2.get().strip()
            if not x1 or not y1 or not x2 or not y2:
                self.log_message("All drag-and-drop coordinates (X1, Y1, X2, Y2) must be filled!", "WARNING")
                return
            try:
                int(x1); int(y1); int(x2); int(y2)
            except ValueError:
                self.log_message("Coordinates must be valid integers!", "WARNING")
                return
            aval = f"{x1},{y1},{x2},{y2}"

        self.active_rules[self.selected_rule_index]["actions"].append({
            "type": atype, "value": aval
        })
        
        # Clear fields
        self.entry_act_key.delete(0, "end")
        self.entry_act_text.delete(0, "end")
        self.entry_act_wait.delete(0, "end")
        self.entry_act_cx.delete(0, "end")
        self.entry_act_cy.delete(0, "end")
        self.entry_act_scroll.delete(0, "end")
        self.entry_act_drag_x1.delete(0, "end")
        self.entry_act_drag_y1.delete(0, "end")
        self.entry_act_drag_x2.delete(0, "end")
        self.entry_act_drag_y2.delete(0, "end")
        
        self.render_action_list()
        self.log_message(f"Added Action: '{atype} [{aval}]' to sequence.", "SUCCESS")

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

    def format_action_label(self, act):
        atype = act["type"]
        aval = act["value"]
        
        if atype == "Press Key":
            return f"🖮  Press Key [{aval}]"
        elif atype == "Key Down (Hold)":
            return f"🖮  Hold Key Down [{aval}]"
        elif atype == "Key Up (Release)":
            return f"🖮  Release Key [{aval}]"
        elif atype == "Type Text":
            return f"✍  Type Text: \"{aval}\""
        elif atype == "Wait (ms)":
            return f"⏳  Wait {aval} ms"
        elif atype == "Click Found Spot":
            return f"🖱️  {aval} at Found Spot"
        elif atype == "Click Custom (X,Y)":
            try:
                parts = aval.split(",")
                cx, cy = parts[0], parts[1]
                ctype = parts[2] if len(parts) > 2 else "Left Click"
                return f"🖱️  {ctype} at ({cx}, {cy})"
            except:
                return f"🖱️  Click Custom: {aval}"
        elif atype == "Mouse Scroll":
            return f"🖱️  Scroll Mouse: {aval}"
        elif atype == "Drag and Drop":
            try:
                parts = aval.split(",")
                return f"🖱️  Drag ({parts[0]},{parts[1]}) -> ({parts[2]},{parts[3]})"
            except:
                return f"🖱️  Drag and Drop: {aval}"
        return f"{atype} [{aval}]"

    def render_action_list(self):
        for widget in self.action_scroll.winfo_children():
            widget.destroy()
            
        if self.selected_rule_index is None: return

        actions = self.active_rules[self.selected_rule_index]["actions"]
        
        if not actions:
            ctk.CTkLabel(
                self.action_scroll, text="No actions configured for this rule yet.", 
                font=("Arial", 11, "italic"), text_color=self.color_text_muted
            ).pack(pady=10)
            return
        
        for idx, act in enumerate(actions):
            row = ctk.CTkFrame(self.action_scroll, fg_color="#14141d", border_width=1, border_color=self.color_border)
            row.pack(fill="x", pady=3, padx=5)
            
            label_text = self.format_action_label(act)
            ctk.CTkLabel(
                row, text=label_text, anchor="w", font=("Arial", 12), text_color="#FFFFFF"
            ).pack(side="left", padx=10, fill="x", expand=True)
            
            ctrl_btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            ctrl_btn_frame.pack(side="right", padx=5)
            
            # --- MOVE UP ---
            if idx > 0:
                ctk.CTkButton(
                    ctrl_btn_frame, text="▲", width=25, height=22, fg_color="#2b2b3d", hover_color="#3a3a52",
                    command=lambda i=idx: self.move_action_up(i)
                ).pack(side="left", padx=2)
            else:
                ctk.CTkLabel(ctrl_btn_frame, text=" ", width=25).pack(side="left", padx=2) 

            # --- MOVE DOWN ---
            if idx < len(actions) - 1:
                ctk.CTkButton(
                    ctrl_btn_frame, text="▼", width=25, height=22, fg_color="#2b2b3d", hover_color="#3a3a52",
                    command=lambda i=idx: self.move_action_down(i)
                ).pack(side="left", padx=2)
            else:
                ctk.CTkLabel(ctrl_btn_frame, text=" ", width=25).pack(side="left", padx=2) 

            # --- DELETE ---
            cmd = lambda i=idx: self.delete_action(i)
            ctk.CTkButton(
                ctrl_btn_frame, text="✕", width=25, height=22, 
                fg_color="transparent", hover_color=self.color_danger, 
                text_color=self.color_danger, font=("Arial", 12, "bold"),
                command=cmd
            ).pack(side="right", padx=5)

    def delete_action(self, action_index):
        if self.selected_rule_index is not None:
            removed = self.active_rules[self.selected_rule_index]["actions"].pop(action_index)
            self.log_message(f"Deleted Action: {removed['type']}")
            self.render_action_list()

    # =======================================================
    # SYSTEM LOGIC: SAVE & LOAD CONFIGURATION CHAINS
    # =======================================================
    def save_logic_chain(self):
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            initialdir=".",
            title="Save Active Sequence Chain",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if not filename: return
        
        # Serialize only pure details (strip template references)
        serialized = []
        for rule in self.active_rules:
            serialized.append({
                "name": rule["name"],
                "data": rule["data"],
                "actions": rule["actions"],
                "tolerance": rule.get("tolerance", 20),
                "confidence": rule.get("confidence", 0.8),
                "full_screen": rule.get("full_screen", rule["data"].get("full_screen", False)),
                "invert_match": rule.get("invert_match", rule["data"].get("invert_match", False))
            })
            
        try:
            with open(filename, "w") as f:
                json.dump(serialized, f, indent=4)
            self.log_message(f"Successfully saved active logic chain to {os.path.basename(filename)}", "SUCCESS")
        except Exception as e:
            self.log_message(f"Failed to save logic chain configuration: {e}", "ERROR")

    def load_logic_chain(self):
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            initialdir=".",
            title="Load Sequence Chain",
            filetypes=[("JSON Files", "*.json")]
        )
        if not filename: return
        
        try:
            with open(filename, "r") as f:
                loaded_data = json.load(f)
            
            # Simple integrity validation
            if not isinstance(loaded_data, list):
                self.log_message("Invalid chain configuration file format!", "ERROR")
                return
                
            self.active_rules = []
            for item in loaded_data:
                self.active_rules.append({
                    "name": item["name"],
                    "data": item["data"],
                    "actions": item["actions"],
                    "tolerance": item.get("tolerance", 20),
                    "confidence": item.get("confidence", 0.8),
                    "full_screen": item.get("full_screen", item["data"].get("full_screen", False)),
                    "invert_match": item.get("invert_match", item["data"].get("invert_match", False))
                })
                
            self.selected_rule_index = None
            self.render_rule_list()
            self.render_action_list()
            
            self.editor_container.pack_forget()
            self.placeholder_frame.pack(fill="both", expand=True)
            self.editor_label.configure(text="Rule Sequence Editor")
            
            self.log_message(f"Successfully loaded chain config from {os.path.basename(filename)} ({len(self.active_rules)} rules)", "SUCCESS")
        except Exception as e:
            self.log_message(f"Failed to load logic chain configuration: {e}", "ERROR")

    # =======================================================
    # THE AUTOMATION ENGINE BACKGROUND EXECUTION
    # =======================================================
    def start_automation(self):
        if not self.active_rules: 
            self.log_message("Cannot start engine: active rules chain is empty!", "WARNING")
            return
            
        self.running = True
        self.start_btn.configure(state="disabled", fg_color="#182d1f")
        self.stop_btn.configure(state="normal", fg_color=self.color_danger)
        
        # Visual engine status indicators
        self.led_indicator.configure(fg_color=self.color_success)
        self.status_label.configure(text="ENGINE ACTIVE", text_color=self.color_success)
        
        self.bot_thread = threading.Thread(target=self.automation_loop)
        self.bot_thread.daemon = True
        self.bot_thread.start()

    def stop_automation(self):
        self.running = False
        self.start_btn.configure(state="normal", fg_color=self.color_success)
        self.stop_btn.configure(state="disabled", fg_color="#331414")
        
        # Visual engine status indicators
        self.led_indicator.configure(fg_color=self.color_danger)
        self.status_label.configure(text="ENGINE STOPPED", text_color=self.color_danger)

    def execute_click(self, button_type, x, y):
        if not pydirectinput: return
        try:
            # Humanize mode: add dynamic random coordinate offset and click hold duration
            if hasattr(self, 'switch_humanize') and self.switch_humanize.get() == 1:
                # Random offset between -4 and +4 pixels in both X and Y
                offset_x = random.randint(-4, 4)
                offset_y = random.randint(-4, 4)
                x += offset_x
                y += offset_y
                
                # Organic click-hold time: Sleep between press down and release
                hold_duration = random.uniform(0.055, 0.125)
                
                if button_type == "Right Click":
                    pydirectinput.mouseDown(x, y, button="right")
                    time.sleep(hold_duration)
                    pydirectinput.mouseUp(x, y, button="right")
                elif button_type == "Double Click":
                    # Double click: two single clicks with a small random gap
                    pydirectinput.mouseDown(x, y, button="left")
                    time.sleep(random.uniform(0.04, 0.08))
                    pydirectinput.mouseUp(x, y, button="left")
                    
                    time.sleep(random.uniform(0.12, 0.18))  # Interval between double clicks
                    
                    pydirectinput.mouseDown(x, y, button="left")
                    time.sleep(random.uniform(0.04, 0.08))
                    pydirectinput.mouseUp(x, y, button="left")
                else:
                    pydirectinput.mouseDown(x, y, button="left")
                    time.sleep(hold_duration)
                    pydirectinput.mouseUp(x, y, button="left")
                    
                self.log_message(f"Humanized Click at ({x}, {y}) (offset: {offset_x:+d}, {offset_y:+d}px, hold: {int(hold_duration*1000)}ms)", "INFO")
            else:
                # Normal instant pixel-perfect click
                if button_type == "Right Click":
                    pydirectinput.rightClick(x, y)
                elif button_type == "Double Click":
                    pydirectinput.doubleClick(x, y)
                else:
                    pydirectinput.click(x, y)
        except Exception as e:
            self.log_message(f"Mouse click simulation failed at ({x}, {y}): {e}", "ERROR")

    def automation_loop(self):
        self.log_message("Background automation processing loop started.", "ENGINE")
        
        # Pre-load OpenCV image search templates
        for rule in self.active_rules:
            if rule['data'].get('type') == 'image':
                path = rule['data']['image_path']
                try:
                    img = cv2.imread(path, 0)
                    if img is not None:
                        rule['template'] = img
                        h, w = img.shape
                        rule['size'] = (w, h)
                    else:
                        self.log_message(f"Failed to parse image file: '{path}'", "ERROR")
                except Exception as ex:
                    self.log_message(f"Template load error for {path}: {ex}", "ERROR")

        with mss.mss() as sct:
            while self.running:
                try:
                    loop_speed_ms = float(self.slider_loop_speed.get())
                    loop_interval = loop_speed_ms / 1000.0
                except:
                    loop_interval = 0.1
                    
                for rule in self.active_rules:
                    if not self.running: break
                    
                    found = False
                    found_x, found_y = 0, 0
                    data = rule['data']

                    # --- PIXEL CHECK ---
                    if data.get('type') == 'pixel':
                        try:
                            px_x = int(data["x"])
                            px_y = int(data["y"])
                            monitor = {"top": px_y, "left": px_x, "width": 1, "height": 1}
                            img = sct.grab(monitor)
                            pixel = img.pixel(0, 0)
                            
                            target = list(map(int, data["rgb"].split(',')))
                            tolerance = rule.get("tolerance", data.get("tolerance", 20))
                            
                            diff = math.sqrt(sum((a - b) ** 2 for a, b in zip(pixel, target)))
                            
                            is_invert = rule.get("invert_match", data.get("invert_match", False))
                            base_found = diff < tolerance
                            found = not base_found if is_invert else base_found
                            
                            if found:
                                found_x, found_y = px_x, px_y
                        except: 
                            pass

                    # --- IMAGE CHECK ---
                    elif data.get('type') == 'image' and 'template' in rule:
                        try:
                            is_fs = rule.get("full_screen", data.get("full_screen", False))
                            region = data.get("region")
                            
                            if not is_fs and region:
                                rx1, ry1, rx2, ry2 = region
                                pad = 10
                                primary = sct.monitors[1]
                                px1 = max(primary["left"], rx1 - pad)
                                py1 = max(primary["top"], ry1 - pad)
                                px2 = min(primary["left"] + primary["width"], rx2 + pad)
                                py2 = min(primary["top"] + primary["height"], ry2 + pad)
                                
                                monitor = {
                                    "left": int(px1),
                                    "top": int(py1),
                                    "width": int(px2 - px1),
                                    "height": int(py2 - py1)
                                }
                                # Safeguard against grabbed image being smaller than template
                                w, h = rule['size']
                                if monitor["width"] < w or monitor["height"] < h:
                                    monitor = sct.monitors[1]
                            else:
                                monitor = sct.monitors[1]
                                
                            sct_img = np.array(sct.grab(monitor))
                            gray_screen = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2GRAY)
                            res = cv2.matchTemplate(gray_screen, rule['template'], cv2.TM_CCOEFF_NORMED)
                            
                            confidence = rule.get("confidence", data.get("confidence", 0.8))
                            loc = np.where(res >= confidence) 
                            
                            is_invert = rule.get("invert_match", data.get("invert_match", False))
                            base_found = len(loc[0]) > 0
                            found = not base_found if is_invert else base_found
                            
                            if found:
                                if base_found:
                                    pt = list(zip(*loc[::-1]))[0] 
                                    w, h = rule['size']
                                    found_x = int(monitor["left"] + pt[0] + w/2)
                                    found_y = int(monitor["top"] + pt[1] + h/2)
                                else:
                                    # Fallback coordinate centering if image absent
                                    if region:
                                        found_x = int((region[0] + region[2])/2)
                                        found_y = int((region[1] + region[3])/2)
                                    else:
                                        found_x = int(monitor["left"] + monitor["width"]/2)
                                        found_y = int(monitor["top"] + monitor["height"]/2)
                        except: 
                            pass

                    # --- EXECUTE SEQUENCED ACTIONS ---
                    if found and self.running:
                        rule_name = os.path.basename(rule['name'])
                        self.log_message(f"Rule MATCHED: '{rule_name}' at coordinates ({found_x}, {found_y})", "ENGINE")
                        
                        for action in rule['actions']:
                            if not self.running: break
                            atype = action['type']
                            aval = action['value']

                            try:
                                if atype == "Press Key":
                                    if pydirectinput: 
                                        if self.switch_humanize.get() == 1:
                                            # Simulates holding key down organically
                                            hold_time = random.uniform(0.045, 0.095)
                                            pydirectinput.keyDown(aval)
                                            time.sleep(hold_time)
                                            pydirectinput.keyUp(aval)
                                            self.log_message(f"Executed: Pressed Key [{aval}] (hold: {int(hold_time*1000)}ms)", "INFO")
                                        else:
                                            pydirectinput.press(aval)
                                            self.log_message(f"Executed: Pressed Key [{aval}]", "INFO")
                                
                                elif atype == "Type Text":
                                    if self.switch_humanize.get() == 1:
                                        # Character-by-character typing with organic speed variance and hesitations
                                        text_str = str(aval)
                                        for char in text_str:
                                            if not self.running: break
                                            keyboard.write(char)
                                            delay = random.uniform(0.035, 0.110)
                                            if random.random() < 0.05:
                                                delay += random.uniform(0.15, 0.3)
                                            time.sleep(delay)
                                        self.log_message(f"Executed: Humanized typed text sequence: \"{aval}\"", "INFO")
                                    else:
                                        keyboard.write(str(aval), delay=0.05)
                                        self.log_message(f"Executed: Typed text sequence: \"{aval}\"", "INFO")
                                
                                elif atype == "Wait (ms)":
                                    wait_val = float(aval)
                                    if self.switch_humanize.get() == 1:
                                        # Timing jitter ±15%
                                        jitter = random.uniform(-0.15, 0.15)
                                        wait_val = max(10.0, wait_val * (1.0 + jitter))
                                        self.log_message(f"Executed: Waited {int(wait_val)} ms (jittered from {aval} ms)", "INFO")
                                    else:
                                        self.log_message(f"Executed: Waited {aval} ms", "INFO")
                                    time.sleep(wait_val / 1000.0)
                                
                                elif atype == "Click Found Spot":
                                    ctype = aval if aval in ["Left Click", "Right Click", "Double Click"] else "Left Click"
                                    if pydirectinput:
                                        self.execute_click(ctype, found_x, found_y)
                                        self.log_message(f"Executed: {ctype} at match center ({found_x}, {found_y})", "INFO")

                                elif atype == "Click Custom (X,Y)":
                                    coords = aval.split(',')
                                    cx = int(coords[0].strip())
                                    cy = int(coords[1].strip())
                                    ctype = coords[2].strip() if len(coords) > 2 else "Left Click"
                                    if pydirectinput:
                                        self.execute_click(ctype, cx, cy)
                                        self.log_message(f"Executed: {ctype} at Custom Target ({cx}, {cy})", "INFO")

                                elif atype == "Key Down (Hold)":
                                    if pydirectinput:
                                        pydirectinput.keyDown(aval)
                                        self.log_message(f"Executed: Key Down [{aval}]", "INFO")

                                elif atype == "Key Up (Release)":
                                    if pydirectinput:
                                        pydirectinput.keyUp(aval)
                                        self.log_message(f"Executed: Key Up [{aval}]", "INFO")

                                elif atype == "Mouse Scroll":
                                    if pydirectinput:
                                        scroll_amt = int(aval)
                                        pydirectinput.scroll(scroll_amt)
                                        self.log_message(f"Executed: Mouse Scroll [{scroll_amt}]", "INFO")

                                elif atype == "Drag and Drop":
                                    if pydirectinput:
                                        parts = aval.split(",")
                                        dx1, dy1 = int(parts[0]), int(parts[1])
                                        dx2, dy2 = int(parts[2]), int(parts[3])
                                        
                                        # Humanized smooth drag S-curve timing
                                        dist = math.hypot(dx2 - dx1, dy2 - dy1)
                                        steps = max(12, int(dist / 12))
                                        duration = random.uniform(0.35, 0.65)
                                        time_step = duration / steps
                                        
                                        pydirectinput.moveTo(dx1, dy1)
                                        time.sleep(random.uniform(0.06, 0.12))
                                        pydirectinput.mouseDown(dx1, dy1, button="left")
                                        time.sleep(random.uniform(0.06, 0.12))
                                        
                                        for i in range(1, steps + 1):
                                            t = i / steps
                                            ease_t = (math.sin((t - 0.5) * math.pi) + 1.0) / 2.0
                                            curr_x = int(dx1 + (dx2 - dx1) * ease_t)
                                            curr_y = int(dy1 + (dy2 - dy1) * ease_t)
                                            
                                            # Apply S-curve hand tremor deviation in Humanize mode
                                            if self.switch_humanize.get() == 1:
                                                curr_x += random.randint(-1, 1)
                                                curr_y += random.randint(-1, 1)
                                                
                                            pydirectinput.moveTo(curr_x, curr_y)
                                            time.sleep(time_step)
                                            
                                        pydirectinput.moveTo(dx2, dy2)
                                        time.sleep(random.uniform(0.06, 0.12))
                                        pydirectinput.mouseUp(dx2, dy2, button="left")
                                        self.log_message(f"Executed: Dragged from ({dx1}, {dy1}) to ({dx2}, {dy2})", "INFO")
                            except Exception as act_ex:
                                self.log_message(f"Action Execution Error ({atype}): {act_ex}", "ERROR")
                        
                        # Prevent immediate rule multi-trigger overlap
                        if self.switch_humanize.get() == 1:
                            time.sleep(random.uniform(0.42, 0.58))
                        else:
                            time.sleep(0.5)

                if self.switch_humanize.get() == 1:
                    jitter = random.uniform(-0.15, 0.15)
                    actual_loop_interval = max(0.01, loop_interval * (1.0 + jitter))
                else:
                    actual_loop_interval = loop_interval
                time.sleep(actual_loop_interval)
                
        self.log_message("Background automation processing loop stopped.", "ENGINE")

    # =======================================================
    # SCREENSHOT OVERLAYS & PRECISE CAPTURE VIEWPORTS
    # =======================================================
    def start_overlay(self, mode):
        self.capture_mode = mode
        self.withdraw()
        # Sleep slightly to let the window fully hide from capture
        self.after(200, self.launch_overlay)

    def launch_overlay(self):
        self.screenshot_img = ImageGrab.grab(all_screens=True)
        self.tk_image = ImageTk.PhotoImage(self.screenshot_img)
        self.overlay = ctk.CTkToplevel(self)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        
        # Hide borders/headers for absolute fullscreen selection feel
        self.overlay.overrideredirect(True)
        
        self.canvas = ctk.CTkCanvas(
            self.overlay, 
            width=self.screenshot_img.width, 
            height=self.screenshot_img.height, 
            cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
        
        # Semi-transparent overlay block for instructions
        self.canvas.create_rectangle(
            0, 0, self.screenshot_img.width, 45, 
            fill="#07070a", outline=""
        )

        if self.capture_mode == "pixel":
            inst = "PIXEL COLOR SELECTOR  |  Move cursor and click to capture color. Right-click to cancel."
        elif self.capture_mode == "coord":
            inst = "COORDINATES SELECTOR  |  Move cursor and click to choose custom click target. Right-click to cancel."
        else:
            inst = "IMAGE TEMPLATE SELECTOR  |  Drag left-click to outline target search frame. Right-click to cancel."

        self.overlay_text = self.canvas.create_text(
            self.screenshot_img.width // 2, 22, 
            text=inst, 
            fill=self.color_accent, 
            font=("Arial", 14, "bold"), 
            justify="center"
        )
        
        # Real-time tracking and zoom magnifiers
        self.canvas.bind("<Motion>", self.on_overlay_mouse_move)
        
        if self.capture_mode in ["pixel", "coord", "drag_start", "drag_end"]:
            self.canvas.bind("<Button-1>", self.on_overlay_click)
        else:
            self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
            self.canvas.bind("<B1-Motion>", self.on_drag_motion)
            self.canvas.bind("<ButtonRelease-1>", self.on_drag_release)
            
        # Right-click cancels selection and restores main app
        self.canvas.bind("<Button-3>", lambda e: (self.overlay.destroy(), self.deiconify()))

    def on_overlay_mouse_move(self, event):
        x, y = event.x, event.y
        if 0 <= x < self.screenshot_img.width and 0 <= y < self.screenshot_img.height:
            try:
                rgb = self.screenshot_img.getpixel((x, y))
            except:
                rgb = (0,0,0)
                
            # Update coordinate HUD inside instruction frame
            if self.capture_mode == "pixel":
                text_str = f"PIXEL COLOR SELECTOR  |  Cursor: ({x}, {y}) | RGB: {rgb[0]},{rgb[1]},{rgb[2]}  |  Click to select. Right-click to cancel."
            elif self.capture_mode == "coord":
                text_str = f"COORDINATES SELECTOR  |  Cursor Target: ({x}, {y})  |  Click to select click location. Right-click to cancel."
            elif self.capture_mode == "drag_start":
                text_str = f"DRAG START SELECTOR  |  Cursor: ({x}, {y})  |  Click to select Drag Start spot. Right-click to cancel."
            elif self.capture_mode == "drag_end":
                text_str = f"DRAG END SELECTOR  |  Cursor: ({x}, {y})  |  Click to select Drag End spot. Right-click to cancel."
            else:
                text_str = f"IMAGE TEMPLATE SELECTOR  |  Drag Start: ({self.start_x}, {self.start_y}) -> Cursor: ({x}, {y})  |  Right-click to cancel."
                
            self.canvas.itemconfigure(self.overlay_text, text=text_str)

            # Draw a beautiful magnifying glass with crosshair when picking pixel
            if self.capture_mode == "pixel":
                zoom_r = 10  # 21x21 selection region
                x1, y1 = max(0, x - zoom_r), max(0, y - zoom_r)
                x2, y2 = min(self.screenshot_img.width, x + zoom_r), min(self.screenshot_img.height, y + zoom_r)
                
                try:
                    crop_region = self.screenshot_img.crop((x1, y1, x2, y2))
                    # Rescale 6x for rich retro-grid zoom visibility
                    crop_zoom = crop_region.resize((120, 120), Image.Resampling.NEAREST)
                    self.zoom_tk_image = ImageTk.PhotoImage(crop_zoom)
                    
                    # Compute safe offset box coords so the magnifying viewport doesn't hide the cursor
                    zoom_x = x + 35 if x + 160 < self.screenshot_img.width else x - 155
                    zoom_y = y + 35 if y + 160 < self.screenshot_img.height else y - 155
                    
                    if hasattr(self, 'zoom_rect_id'): self.canvas.delete(self.zoom_rect_id)
                    if hasattr(self, 'zoom_img_id'): self.canvas.delete(self.zoom_img_id)
                    if hasattr(self, 'zoom_cross_h_id'): self.canvas.delete(self.zoom_cross_h_id)
                    if hasattr(self, 'zoom_cross_v_id'): self.canvas.delete(self.zoom_cross_v_id)
                    
                    self.zoom_img_id = self.canvas.create_image(zoom_x, zoom_y, image=self.zoom_tk_image, anchor="nw")
                    self.zoom_rect_id = self.canvas.create_rectangle(zoom_x, zoom_y, zoom_x + 120, zoom_y + 120, outline=self.color_accent, width=2)
                    
                    # Horizontal and vertical crosshairs in central grid
                    cx, cy = zoom_x + 60, zoom_y + 60
                    self.zoom_cross_h_id = self.canvas.create_line(cx - 12, cy, cx + 12, cy, fill="#FF3D00", width=1)
                    self.zoom_cross_v_id = self.canvas.create_line(cx, cy - 12, cx, cy + 12, fill="#FF3D00", width=1)
                except:
                    pass

    def on_overlay_click(self, event):
        x, y = event.x, event.y
        self.overlay.destroy()
        self.deiconify()
        
        if self.capture_mode == "pixel":
            try:
                rgb = self.screenshot_img.getpixel((x, y))
            except:
                rgb = (0, 0, 0)
            self.entry_X.delete(0, "end"); self.entry_X.insert(0, str(x))
            self.entry_Y.delete(0, "end"); self.entry_Y.insert(0, str(y))
            self.entry_RGB.delete(0, "end"); self.entry_RGB.insert(0, f"{rgb[0]}, {rgb[1]}, {rgb[2]}")
            self.entry_Image.delete(0, "end")
            
            # Clear last capture region
            self.last_capture_region = None
            
            self.update_pixel_preview()
            self.update_image_preview()
            self.log_message(f"Captured pixel coords ({x}, {y}) color: RGB({rgb[0]},{rgb[1]},{rgb[2]})", "SUCCESS")
            
        elif self.capture_mode == "coord":
            self.entry_act_cx.delete(0, "end"); self.entry_act_cx.insert(0, str(x))
            self.entry_act_cy.delete(0, "end"); self.entry_act_cy.insert(0, str(y))
            self.log_message(f"Selected Custom Coordinates for click: ({x}, {y})", "SUCCESS")
            
        elif self.capture_mode == "drag_start":
            self.entry_act_drag_x1.delete(0, "end"); self.entry_act_drag_x1.insert(0, str(x))
            self.entry_act_drag_y1.delete(0, "end"); self.entry_act_drag_y1.insert(0, str(y))
            self.log_message(f"Selected Drag Start Coordinates: ({x}, {y})", "SUCCESS")
            
        elif self.capture_mode == "drag_end":
            self.entry_act_drag_x2.delete(0, "end"); self.entry_act_drag_x2.insert(0, str(x))
            self.entry_act_drag_y2.delete(0, "end"); self.entry_act_drag_y2.insert(0, str(y))
            self.log_message(f"Selected Drag End Coordinates: ({x}, {y})", "SUCCESS")

    def on_drag_start(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=self.color_accent, width=2)

    def on_drag_motion(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_drag_release(self, event):
        self.overlay.destroy()
        self.deiconify()
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        
        # Safeguard selection sizing
        if x2 - x1 < 2 or y2 - y1 < 2:
            self.log_message("Captured frame region too small, selection canceled.", "WARNING")
            return
            
        try:
            crop = self.screenshot_img.crop((x1, y1, x2, y2))
            if not os.path.exists("images"): 
                os.makedirs("images")
            filename = f"images/cap_{int(time.time())}.png"
            crop.save(filename)
            
            self.entry_Image.delete(0, "end"); self.entry_Image.insert(0, filename)
            self.entry_X.delete(0, "end"); self.entry_Y.delete(0, "end"); self.entry_RGB.delete(0, "end")
            
            # Save the captured region coordinates
            self.last_capture_region = (x1, y1, x2, y2)
            
            self.update_pixel_preview()
            self.update_image_preview()
            self.log_message(f"Successfully captured image template and saved to: {filename}", "SUCCESS")
        except Exception as e:
            self.log_message(f"Failed saving cropped template: {e}", "ERROR")

    # =======================================================
    # PROFILE STORAGE & REGISTRY INTERACT
    # =======================================================
    def save_new_profile(self):
        name = self.entry_Name.get().strip()
        if not name: 
            self.log_message("Please fill out a unique Profile Name before saving!", "WARNING")
            return
            
        image_path = self.entry_Image.get().strip()
        
        if image_path:
            conf = round(float(self.slider_confidence.get()), 2)
            full_screen = self.checkbox_full_screen.get() == 1
            invert_match = self.checkbox_image_invert.get() == 1
            data = {
                "type": "image", 
                "image_path": image_path,
                "confidence": conf,
                "full_screen": full_screen,
                "invert_match": invert_match
            }
            if hasattr(self, 'last_capture_region') and self.last_capture_region:
                data["region"] = list(self.last_capture_region)
        else:
            x_coord = self.entry_X.get().strip()
            y_coord = self.entry_Y.get().strip()
            rgb_val = self.entry_RGB.get().strip()
            
            if not x_coord or not y_coord or not rgb_val:
                self.log_message("Create Detector error: No pixel coordinates or RGB data filled!", "ERROR")
                return
                
            tol = int(self.slider_tolerance.get())
            invert_match = self.checkbox_pixel_invert.get() == 1
            data = {
                "type": "pixel", 
                "x": x_coord, 
                "y": y_coord, 
                "rgb": rgb_val,
                "tolerance": tol,
                "invert_match": invert_match
            }
            
        try:
            filename = f"{name}.json"
            with open(filename, "w") as f: 
                json.dump(data, f, indent=4)
            self.save_status.configure(text=f"Saved profile '{filename}'!", text_color=self.color_success)
            self.log_message(f"Registered new detector profile: '{filename}'", "SUCCESS")
            
            # Clear Fields
            self.entry_Name.delete(0, "end")
            self.entry_Image.delete(0, "end")
            self.entry_X.delete(0, "end")
            self.entry_Y.delete(0, "end")
            self.entry_RGB.delete(0, "end")
            self.last_capture_region = None
            self.checkbox_full_screen.deselect()
            self.checkbox_image_invert.deselect()
            self.checkbox_pixel_invert.deselect()
            self.update_pixel_preview()
            self.update_image_preview()
            
            self.refresh_profiles()
        except Exception as e:
            self.log_message(f"Failed to register detector profile: {e}", "ERROR")

if __name__ == "__main__":
    app = PixelAutomationApp()
    app.mainloop()