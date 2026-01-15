"""
Advanced Sprite Separator & Naming Tool for AgriVidya
- Select multiple images -> they open one-by-one
- Draw rectangles to select sprites
- Sidebar shows thumbnail + name box + Asset/Animation toggle + order label + delete
- Drag sidebar items to reorder (updates animation order automatically)
- Save & Next: trims transparent pixels, saves PNGs with naming rules and writes assets/split_sprites.json
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import json, os
import prerequisites
import time
import threading
prerequisites.check_and_install()

def trim_transparent(im):
    """Trim transparent borders from an RGBA image. Returns trimmed image and bbox relative to original."""
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    px = im.getdata()
    # Create alpha-based bbox
    bbox = im.split()[-1].getbbox()  # returns (left, upper, right, lower) or None
    if bbox:
        return im.crop(bbox), bbox
    else:
        # fully transparent
        return im, (0, 0, im.width, im.height)

class SidebarItem(tk.Frame):
    """A single sidebar entry: thumbnail, text entry, toggle, order label, delete button. Draggable."""
    def __init__(self, parent, preview_img, default_name, on_delete, on_toggle_change, on_reorder_request):
        super().__init__(parent, bg="#eee", relief="raised", bd=1)
        self.parent = parent
        self.on_delete = on_delete
        self.on_toggle_change = on_toggle_change
        self.on_reorder_request = on_reorder_request

        # Thumbnail
        self.preview_tk = ImageTk.PhotoImage(preview_img)
        self.thumb = tk.Label(self, image=self.preview_tk, bg="#ddd")
        self.thumb.image = self.preview_tk
        self.thumb.pack(side="left", padx=4, pady=4)

        # Controls frame
        ctr = tk.Frame(self, bg="#eee")
        ctr.pack(side="left", fill="both", expand=True, padx=2, pady=2)

        # Name entry
        self.name_entry = tk.Entry(ctr)
        self.name_entry.insert(0, default_name)
        self.name_entry.pack(fill="x", pady=(4,2))
        self.name_entry.bind("<KeyRelease>", lambda e: self.on_toggle_change())

        # Row for toggle, order label and delete
        bottom = tk.Frame(ctr, bg="#eee")
        bottom.pack(fill="x", pady=(0,4))

        self.is_animation = tk.BooleanVar()
        self.chk = tk.Checkbutton(bottom, text="Animation", variable=self.is_animation,
                                  bg="#eee", command=self._toggle_changed)
        self.chk.pack(side="left")

        self.order_label = tk.Label(bottom, text="", width=4, bg="#eee")
        self.order_label.pack(side="left", padx=6)

        self.del_btn = tk.Button(bottom, text="Delete", command=self._delete, width=6)
        self.del_btn.pack(side="right")

        # Drag events
        self.bind("<ButtonPress-1>", self.on_drag_start)
        self.bind("<B1-Motion>", self.on_drag_motion)
        self.bind("<ButtonRelease-1>", self.on_drag_release)
        for child in self.winfo_children():
            child.bind("<ButtonPress-1>", self.on_drag_start)
            child.bind("<B1-Motion>", self.on_drag_motion)
            child.bind("<ButtonRelease-1>", self.on_drag_release)

        self._drag_start_y = None

    def _delete(self):
        self.on_delete(self)

    def _toggle_changed(self):
        self.on_toggle_change()

    def set_order(self, n):
        self.order_label.config(text=str(n) if n is not None else "")

    # ---- Drag handlers (calls parent reorder callback with y)
    def on_drag_start(self, event):
        self._drag_start_y = event.y_root
        # raise visual
        self.lift()

    def on_drag_motion(self, event):
        dy = event.y_root - self._drag_start_y
        self.place_configure(rely=0, y=self.winfo_y() + dy)  # relative moving
        self._drag_start_y = event.y_root
        self.on_reorder_request(self, event.y_root)

    def on_drag_release(self, event):
        self.place_forget()
        self.on_reorder_request(self, event.y_root, finalize=True)

class SpriteExtractor:
    def __init__(self, root, image_paths):
        self.root = root
        self.image_paths = list(image_paths)
        self.current_index = 0
        self.frames_meta = {}  # final JSON frames
        self.output_folder = os.path.join("assets", "sprites")
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs("assets", exist_ok=True)
        self.show_grid = tk.BooleanVar(value=True)
        self.grid_level = tk.IntVar(value=0)  # 0=8,1=16,2=32,3=64

        self.load_image()

        self.root.bind("<Up>", lambda e: self.move_image(0, -1))
        self.root.bind("<Down>", lambda e: self.move_image(0, 1))
        self.root.bind("<Left>", lambda e: self.move_image(-1, 0))
        self.root.bind("<Right>", lambda e: self.move_image(1, 0))
        self.history = []
        self.redo_stack = []
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

        # Background removal
        self.bg_remove_enabled = False
        self.bg_remove_color = None  # (R,G,B) or None
        self.bg_pick_mode = False

        # Grid toggle checkbox
        grid_toggle_frame = tk.Frame(self.canvas_container, bg="#333")
        grid_toggle_frame.place(x=4, y=50, anchor="nw")
        tk.Checkbutton(grid_toggle_frame, text="Show Grid", variable=self.show_grid,
                    bg="#333", fg="white", selectcolor="#333",
                    command=self.draw_grid).pack()

        # Grid size radio buttons
        size_frame = tk.Frame(self.canvas_container, bg="#333")
        size_frame.place(x=4, y=80, anchor="nw")
        tk.Label(size_frame, text="Grid Size:", bg="#333", fg="white").pack(side="left")
        for i, size in enumerate(reversed(self.grid_sizes)):
            tk.Radiobutton(
                size_frame,
                text=f"{size}x{size}",
                variable=self.grid_level,
                value=i,
                bg="#333", fg="white", selectcolor="#333",
                command=self.draw_grid
            ).pack(side="left")

    def load_image(self):
        if self.current_index >= len(self.image_paths):
            self.finish()
            return

        # Load image
        self.image_path = self.image_paths[self.current_index]
        self.img_full = Image.open(self.image_path).convert("RGBA")

        # Clear previous UI
        for w in self.root.winfo_children():
            w.destroy()

        # Fixed initial window size
        self.root.attributes("-fullscreen", True)
        self.root.resizable(False, False)
        self.root.title(f"Sprite Extractor - {os.path.basename(self.image_path)}")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Main container
        self.main_container = tk.Frame(self.root)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.main_container.rowconfigure(0, weight=1)
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.columnconfigure(1, weight=0)

        # Left: canvas container
        self.canvas_container = tk.Frame(self.main_container, bg="#333")
        self.canvas_container.grid(row=0, column=0, sticky="nsew")
        self.canvas_container.rowconfigure(0, weight=1)
        self.canvas_container.columnconfigure(0, weight=1)

        # Canvas
        self.canvas_bg_color = tk.StringVar(value="#222")
        self.canvas = tk.Canvas(self.canvas_container, cursor="cross", bg=self.canvas_bg_color.get())
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas_image_id = self.canvas.create_image(0, 0, anchor="nw")
        self.root.bind_all("<Control-MouseWheel>", self.on_ctrl_mousewheel)

        # --- Grid Snap toggle ---
        self.grid_snap = tk.BooleanVar(value=False)
        snap_frame = tk.Frame(self.canvas_container, bg="#333")
        snap_frame.place(x=4, y=4, anchor="nw")

        tk.Checkbutton(
            snap_frame,
            text="Snap to Grid",
            variable=self.grid_snap,
            bg="#333",
            fg="white",
            selectcolor="#333"
        ).pack()

        # Visual grid options
        self.grid_sizes = [8, 16, 32, 64]
        self.grid_thickness = [0.5, 0.5, 0.5, 0.5]
        self.grid_level = tk.IntVar(value=0)

        # Resize handling
        self._resize_canvas()
        self.canvas.bind("<Configure>", lambda e: self._resize_canvas())

        # Canvas background color radio buttons
        color_frame = tk.Frame(self.canvas_container, bg="#333")
        color_frame.place(relx=1.0, rely=0, anchor="ne")
        tk.Label(color_frame, text="BG Color:", bg="#333", fg="white").pack(side="left", padx=2)
        tk.Radiobutton(color_frame, text="Black", variable=self.canvas_bg_color, value="#222",
                    bg="#333", fg="white", selectcolor="#333", command=self.update_canvas_bg).pack(side="left")
        tk.Radiobutton(color_frame, text="White", variable=self.canvas_bg_color, value="#fff",
                    bg="#333", fg="black", selectcolor="#333", command=self.update_canvas_bg).pack(side="left")

        # Right: sidebar container
        self.sidebar_container = tk.Frame(self.main_container, width=260, bg="#f5f5f5")
        self.sidebar_container.grid(row=0, column=1, sticky="ns")
        self.sidebar_container.rowconfigure(0, weight=1)
        self.sidebar_container.rowconfigure(1, weight=0)
        self.sidebar_container.rowconfigure(2, weight=0)
        self.sidebar_container.columnconfigure(0, weight=1)

        # Thumbnails scroll area
        self.side_scroll = tk.Canvas(self.sidebar_container, bg="#f5f5f5", highlightthickness=0)
        self.side_scroll.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar = tk.Scrollbar(self.sidebar_container, orient="vertical", command=self.side_scroll.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.side_scroll.configure(yscrollcommand=self.v_scrollbar.set)
        self.side_frame = tk.Frame(self.side_scroll, bg="#f5f5f5")
        self.side_window = self.side_scroll.create_window((0, 0), window=self.side_frame, anchor="nw")
        self.side_frame.bind("<Configure>", lambda e: self.side_scroll.configure(scrollregion=self.side_scroll.bbox("all")))

        # Instructions
        self.instructions = tk.Label(
            self.sidebar_container,
            text=(
                "Instructions:\n"
                "1. Draw a rectangle on the image to select a sprite.\n"
                "2. Use 'Snap to Grid' for precise, grid-aligned selections.\n"
                "3. Use 'Show Grid' and select grid size for visual aid.\n"
                "4. Enter a name for the sprite in the sidebar.\n"
                "5. Drag items in the sidebar to reorder; this updates animation frame order.\n"
                "6. Check 'Animation' for frames that are part of a sequence.\n"
                "7. Enter sprite names; numbering (_1, _2, ...) is added automatically for animations.\n"
                "8. Use arrow keys to nudge the image, Ctrl+MouseWheel to zoom.\n"
                "9. Press 'Save & Next' to save selected sprites and move to the next image.\n"
                "10. It is preferable to first complete one set of tiles in \nthe image before moving to the next as zoom in/out destroys selection orientation."
            ),
            bg="#f5f5f5",
            justify="left"
        )
        self.instructions.grid(row=1, column=0, sticky="ew", padx=4, pady=6)

        # Buttons container
        btn_frame = tk.Frame(self.sidebar_container, bg="#f5f5f5")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=6)

        # Top row
        top_row = tk.Frame(btn_frame, bg="#f5f5f5")
        top_row.pack(side="top", fill="x", pady=2)
        tk.Button(top_row, text="Map & Next", command=self.map_sprites).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(top_row, text="Split & Next", command=self.save_sprites).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(top_row, text="Auto Detect Sprites", command=self.auto_detect_sprites).pack(side="left", expand=True, fill="x", padx=2)

        # Bottom row
        bottom_row = tk.Frame(btn_frame, bg="#f5f5f5")
        bottom_row.pack(side="top", fill="x", pady=2)
        tk.Button(bottom_row, text="Skip", command=self.skip).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(bottom_row, text="Cancel", command=self.root.quit).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(bottom_row, text="Background Remover", command=self.enable_bg_pick).pack(side="left", expand=True, fill="x", padx=2)

        # Internal lists per image
        self.selection_boxes = []
        self.previews = []
        self.sidebar_items = []

        # Draw existing highlights
        self.redraw_highlights()

        # Mouse events
        self.start_x = self.start_y = None
        self.rect_id = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def move_image(self, dx, dy):
        """Move entire image on canvas by dx, dy pixels."""
        self._offset_x += dx
        self._offset_y += dy
        self.canvas.coords(self.canvas_image_id, self._offset_x, self._offset_y)

        # Move highlights as well
        for idx, box in enumerate(self.selection_boxes):
            x1, y1, x2, y2 = box
            self.selection_boxes[idx] = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)

        self.redraw_highlights()

    def enable_bg_pick(self):
        messagebox.showinfo("Pick Color", "Click on the canvas to pick a background color.")
        self.bg_pick_mode = True
        self.canvas.bind("<Button-1>", self.pick_bg_color)

    def pick_bg_color(self, event):
        if not self.bg_pick_mode:
            return
        x, y = self.canvas_to_image_coords(event.x, event.y)
        pixel = self.img_full.getpixel((x, y))
        self.bg_remove_color = pixel[:3]  # RGB only
        self.bg_remove_enabled = True
        self.bg_pick_mode = False
        messagebox.showinfo("Background Color Selected", f"Chosen color: {self.bg_remove_color}")
        # restore normal bindings
        self.canvas.bind("<Button-1>", self.on_press)

    def remove_background(self, img, color, tolerance=20):
        """
        Remove background color by making similar pixels transparent.
        `color` is (R,G,B), tolerance controls how strict the match is.
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            r, g, b, a = item
            if abs(r - color[0]) <= tolerance and abs(g - color[1]) <= tolerance and abs(b - color[2]) <= tolerance:
                new_data.append((r, g, b, 0))  # transparent
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img

    def auto_detect_sprites(self):
        """
        Automatically detect sprites separated by transparent pixels or chosen background color.
        Adds them as sidebar items (highlight + thumbnails) without saving PNGs.
        """
        img = self.img_full.copy()
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        alpha = img.split()[-1]
        visited = set()
        width, height = img.size

        # Decide background removal color
        bg_color = self.bg_remove_color if self.bg_remove_enabled and self.bg_remove_color else None
        tolerance = 20  # pixels within this range are considered background

        # Helper to check if pixel is "transparent" for detection
        def is_transparent(px):
            if bg_color:
                r, g, b, a = px
                return (a == 0) or (
                    abs(r - bg_color[0]) <= tolerance and
                    abs(g - bg_color[1]) <= tolerance and
                    abs(b - bg_color[2]) <= tolerance
                )
            else:
                return px[3] == 0

        # Simple flood-fill detection for non-transparent regions
        def flood_fill(x, y):
            stack = [(x, y)]
            bbox = [x, y, x, y]  # left, top, right, bottom
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in visited:
                    continue
                if cx < 0 or cy < 0 or cx >= width or cy >= height:
                    continue
                pixel = img.getpixel((cx, cy))
                if is_transparent(pixel):
                    continue
                visited.add((cx, cy))
                bbox[0] = min(bbox[0], cx)
                bbox[1] = min(bbox[1], cy)
                bbox[2] = max(bbox[2], cx)
                bbox[3] = max(bbox[3], cy)
                # Add neighbors
                neighbors = [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]
                stack.extend(neighbors)
            return tuple(bbox)

        # Scan all pixels
        for y in range(height):
            for x in range(width):
                pixel = img.getpixel((x, y))
                if (x, y) not in visited and not is_transparent(pixel):
                    x1, y1, x2, y2 = flood_fill(x, y)
                    # Crop the sprite
                    cropped = img.crop((x1, y1, x2+1, y2+1))
                    preview_img = cropped.copy()
                    preview_img.thumbnail((64, 64), Image.NEAREST)

                    # Canvas coords approximation
                    cx1, cy1 = self.image_to_canvas_coords(x1, y1)
                    cx2, cy2 = self.image_to_canvas_coords(x2+1, y2+1)
                    self.selection_boxes.append((cx1, cy1, cx2, cy2))
                    self.previews.append(cropped)

                    # Sidebar item
                    item = SidebarItem(self.side_frame, preview_img, default_name=f"auto_{len(self.sidebar_items)}",
                                    on_delete=self.delete_item,
                                    on_toggle_change=lambda: (self.update_orders(), self.redraw_highlights()),
                                    on_reorder_request=self.handle_reorder_request)
                    item.pack(fill="x", pady=4, padx=4)
                    self.sidebar_items.append(item)

        self.update_orders()
        self.redraw_highlights()
        messagebox.showinfo("Auto Detect", f"Added {len(self.sidebar_items)} auto-detected sprites.")

    def _resize_canvas(self):
        """Scale image to fit canvas while maintaining aspect ratio."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return  # too early
        img_w, img_h = self.img_full.width, self.img_full.height
        ratio = min(canvas_w / img_w, canvas_h / img_h)
        self._scale_w = self._scale_h = ratio
        self._offset_x = (canvas_w - img_w * ratio) / 2
        self._offset_y = (canvas_h - img_h * ratio) / 2
        resized = self.img_full.resize((int(img_w * ratio), int(img_h * ratio)), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.canvas_image_id, image=self.tk_img)
        self.canvas.coords(self.canvas_image_id, self._offset_x, self._offset_y)
        self.redraw_highlights()

    def _resize_canvas(self, event=None):
        """Scale image to fit canvas while maintaining aspect ratio."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return  # too early

        img_w, img_h = self.img_full.width, self.img_full.height
        canvas_ratio = canvas_w / canvas_h
        img_ratio = img_w / img_h

        if canvas_ratio > img_ratio:
            new_h = canvas_h
            new_w = int(img_ratio * new_h)
        else:
            new_w = canvas_w
            new_h = int(new_w / img_ratio)

        # Resize the image for canvas display
        resized = self.img_full.resize((new_w, new_h), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.canvas_image_id, image=self.tk_img)
        self.canvas.image_ref = self.tk_img

        # Save scale and offset for coordinate conversions
        self._scale_w = new_w / img_w
        self._scale_h = new_h / img_h
        self._offset_x = (canvas_w - new_w) / 2
        self._offset_y = (canvas_h - new_h) / 2

        self.canvas.coords(self.canvas_image_id, self._offset_x, self._offset_y)
        self.draw_grid()
        self.redraw_highlights()

    def update_canvas_bg(self):
        self.canvas.config(bg=self.canvas_bg_color.get())

    def redraw_highlights(self):
        self.canvas.delete("highlight")
        for idx, box in enumerate(getattr(self, "selection_boxes", [])):
            cx1, cy1, cx2, cy2 = box  # canvas coordinates directly
            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="red", width=2, tags="highlight")

            # Determine text color based on canvas background
            bg = self.canvas_bg_color.get()
            text_color = "#333300" if bg.lower() in ("#fff", "#ffffff") else "#ffff99"

            # Draw name
            if idx < len(self.sidebar_items):
                name = self.sidebar_items[idx].name_entry.get()
                self.canvas.create_text(cx1 + 4, cy1 + 4, text=name, anchor="nw",
                                        fill=text_color, font=("Arial", 12, "bold"), tags="highlight")

    def canvas_to_image_coords(self, cx, cy):
        """Convert canvas coordinates to original image coordinates using actual canvas scale and offset."""
        if not hasattr(self, "_scale_w"):
            return int(cx), int(cy)  # fallback before first resize

        x = (cx - self._offset_x) / self._scale_w
        y = (cy - self._offset_y) / self._scale_h

        x = max(0, min(self.img_full.width, int(x)))
        y = max(0, min(self.img_full.height, int(y)))
        return x, y

    def image_to_canvas_coords(self, x, y):
        """Convert image coordinates to canvas coordinates using actual canvas scale and offset."""
        if not hasattr(self, "_scale_w"):
            return int(x), int(y)  # fallback before first resize

        cx = x * self._scale_w + self._offset_x
        cy = y * self._scale_h + self._offset_y
        return cx, cy

    def on_ctrl_mousewheel(self, event):
        # 1-pixel zoom in/out
        delta = 1 if event.delta > 0 else -1

        # Mouse position in canvas
        mouse_x, mouse_y = event.x, event.y

        # Convert to image coordinates
        img_x, img_y = self.canvas_to_image_coords(mouse_x, mouse_y)

        # Compute new image size
        new_w = max(1, int(self.img_full.width * self._scale_w) + delta)
        new_h = max(1, int(self.img_full.height * self._scale_h) + delta)

        # Update scale factors
        self._scale_w = new_w / self.img_full.width
        self._scale_h = new_h / self.img_full.height

        # Resize image
        resized = self.img_full.resize((new_w, new_h), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.canvas_image_id, image=self.tk_img)
        self.canvas.image_ref = self.tk_img

        # Adjust offset to keep zoom centered on cursor
        self._offset_x = mouse_x - img_x * self._scale_w
        self._offset_y = mouse_y - img_y * self._scale_h
        self.canvas.coords(self.canvas_image_id, self._offset_x, self._offset_y)

        # Do NOT modify self.selection_boxes; they remain in IMAGE coordinates
        # Redraw highlights in new canvas coordinates
        self.redraw_highlights()

    def save_history(self):
        state = {
            "selection_boxes": list(self.selection_boxes),
            "previews": list(self.previews),
            "sidebar_items_names": [item.name_entry.get() for item in self.sidebar_items],
            "animations": [item.is_animation.get() for item in self.sidebar_items]
        }
        self.history.append(state)
        if len(self.history) > 50:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            return
        state = self.history.pop()
        self.redo_stack.append({
            "selection_boxes": list(self.selection_boxes),
            "previews": list(self.previews),
            "sidebar_items_names": [item.name_entry.get() for item in self.sidebar_items],
            "animations": [item.is_animation.get() for item in self.sidebar_items]
        })
        self.restore_state(state)
        self.redraw_highlights()

    def redo(self):
        if not self.redo_stack:
            return
        state = self.redo_stack.pop()
        self.save_history()
        self.restore_state(state)

    def restore_state(self, state):
        # Clear current sidebar
        for w in self.sidebar_items:
            w.destroy()
        self.sidebar_items = []
        self.selection_boxes = list(state["selection_boxes"])
        self.previews = list(state["previews"])

        # Recreate sidebar items
        for i, cropped in enumerate(self.previews):
            preview_img = cropped.copy()
            preview_img.thumbnail((64, 64), Image.NEAREST)

            item = SidebarItem(
                self.side_frame, preview_img,
                default_name=state["sidebar_items_names"][i],
                on_delete=self.delete_item,
                on_toggle_change=lambda: (self.update_orders(), self.redraw_highlights()),
                on_reorder_request=self.handle_reorder_request
            )
            item.is_animation.set(state["animations"][i])
            item.pack(fill="x", pady=4, padx=4)
            self.sidebar_items.append(item)

        self.update_orders()
        self.redraw_highlights()

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red", width=2)

    def on_drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)
            
            # Draw grid-unit numbers
            self.canvas.delete("coords")
            x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
            x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
            grid_size = self.grid_sizes[self.grid_level.get()]

            # X-axis numbers
            for i, cx in enumerate(range(int(x1), int(x2), grid_size), start=1):
                self.canvas.create_rectangle(cx+1, y1+1, cx+grid_size-1, y1+grid_size-1,
                                            outline="", fill="yellow", stipple="gray50", tags="coords")
                self.canvas.create_text(cx+grid_size//2, y1+grid_size//2,
                                        text=str(i), fill="black", font=("Arial", 8, "bold"), tags="coords")

            # Y-axis numbers
            for i, cy in enumerate(range(int(y1), int(y2), grid_size), start=1):
                self.canvas.create_rectangle(x1+1, cy+1, x1+grid_size-1, cy+grid_size-1,
                                            outline="", fill="red", stipple="gray50", tags="coords")
                self.canvas.create_text(x1+grid_size//2, cy+grid_size//2,
                                        text=str(i), fill="black", font=("Arial", 8, "bold"), tags="coords")

    def on_release(self, event):
        if not self.rect_id:
            return
        cx1, cy1, cx2, cy2 = map(int, self.canvas.coords(self.rect_id))
        cx1, cy1 = self.snap_to_grid(cx1, cy1)
        cx2, cy2 = self.snap_to_grid(cx2, cy2)
        self.save_history()
        
        if abs(cx2 - cx1) < 2 or abs(cy2 - cy1) < 2:
            # invalid / tiny selection
            self.canvas.delete(self.rect_id)
            self.rect_id = None
            return

        # Convert to image coordinates only when cropping
        x1, y1 = self.canvas_to_image_coords(min(cx1, cx2), min(cy1, cy2))
        x2, y2 = self.canvas_to_image_coords(max(cx1, cx2), max(cy1, cy2))
        cropped = self.img_full.crop((x1, y1, x2, y2))
        
        # Thumbnail for sidebar
        preview_img = cropped.copy()
        preview_img.thumbnail((64, 64), Image.NEAREST)

        # Create sidebar item
        item = SidebarItem(self.side_frame, preview_img, default_name=f"sprite_{len(self.sidebar_items)}",
                        on_delete=self.delete_item,
                        on_toggle_change=lambda: (self.update_orders(), self.redraw_highlights()),
                        on_reorder_request=self.handle_reorder_request)
        item.pack(fill="x", pady=4, padx=4)

        # Store **canvas coords for exact highlight**
        self.selection_boxes.append((cx1, cy1, cx2, cy2))
        self.previews.append(cropped)
        self.sidebar_items.append(item)

        self.update_orders()
        self.canvas.delete(self.rect_id)
        self.rect_id = None
        self.redraw_highlights()

    def delete_item(self, item):
        idx = self.sidebar_items.index(item)
        item.destroy()
        del self.sidebar_items[idx]
        del self.selection_boxes[idx]
        del self.previews[idx]
        self.update_orders()
        self.redraw_highlights()
        self.save_history()

    def update_orders(self):
        """
        Set order numbers for animation-checked items based on current sidebar ordering.
        Sidebar shows only numbers for items in sequence per base name.
        """
        # Track counters per base name for display order (optional, can be used for visual hint)
        anim_counters = {}
        for item in self.sidebar_items:
            base_name = item.name_entry.get().strip() or ""
            if item.is_animation.get():
                count = anim_counters.get(base_name, 0) + 1
                anim_counters[base_name] = count
                item.set_order(count)  # display sequence in sidebar
            else:
                item.set_order(None)

    def handle_reorder_request(self, item, y_root, finalize=False):
        """
        Called during dragging of a SidebarItem.
        We will compute new insertion index from y_root relative to side_frame and move item visually when finalize True.
        """
        try:
            idx = self.sidebar_items.index(item)
        except ValueError:
            return

        # convert y_root to coordinate inside side_frame
        abs_x = self.side_frame.winfo_rootx()
        rel_y = y_root - self.side_frame.winfo_rooty()

        # Find target index
        heights = [w.winfo_height() + 8 for w in self.sidebar_items]  # approx including pady
        # compute cumulative sums to find where rel_y falls
        cum = 0
        target = 0
        for i, h in enumerate(heights):
            if rel_y > cum + h/2:
                target = i + 1
            cum += h

        if finalize:
            # Reinsert item widget at target index
            item.pack_forget()
            # remove from lists
            old_idx = self.sidebar_items.index(item)
            self.sidebar_items.pop(old_idx)
            sel = self.selection_boxes.pop(old_idx)
            prev = self.previews.pop(old_idx)
            # reinsert
            self.sidebar_items.insert(target if target <= len(self.sidebar_items) else len(self.sidebar_items), item)
            self.selection_boxes.insert(target if target <= len(self.selection_boxes) else len(self.selection_boxes), sel)
            self.previews.insert(target if target <= len(self.previews) else len(self.previews), prev)
            # repack all in order
            for w in self.sidebar_items:
                w.pack_forget()
            for w in self.sidebar_items:
                w.pack(fill="x", pady=4, padx=4)
            self.update_orders()
        else:
            # During motion, optionally provide visual cue (we don't move until finalize)
            pass

    def snap_to_grid(self, x, y):
        if self.grid_snap.get():
            # Snap to currently selected grid size
            grid_size = self.grid_sizes[self.grid_level.get()]  # 0=8,1=16,2=32,3=64
            x = round(x / grid_size) * grid_size
            y = round(y / grid_size) * grid_size
        return x, y

    def draw_grid(self):
        self.canvas.delete("grid")
        if not self.show_grid.get():
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        size = self.grid_sizes[self.grid_level.get()]
        thickness = self.grid_thickness[self.grid_level.get()]

        # vertical lines
        for x in range(0, canvas_w, size):
            self.canvas.create_line(x, 0, x, canvas_h, fill="#888", width=thickness, tags="grid")
        # horizontal lines
        for y in range(0, canvas_h, size):
            self.canvas.create_line(0, y, canvas_w, y, fill="#888", width=thickness, tags="grid")
        self.redraw_highlights()

    def snap_to_grid(self, x, y):
        if self.grid_snap.get():
            size = self.grid_sizes[self.grid_level.get()]
            x = round(x / size) * size
            y = round(y / size) * size
        return x, y

    def save_sprites(self):
        """
        Save all sprites. Animation frames with same base name get sequential _1, _2 suffixes.
        Opens a folder selection dialog to choose where to save.
        """
        # Ask user for folder where to save this batch
        folder = filedialog.askdirectory(title="Select folder to save sprites")
        if not folder:
            messagebox.showwarning("Cancelled", "Save cancelled. No folder selected.")
            return

        # Track sequential numbering per animation base name
        anim_counters = {}

        saved_count = 0
        for i, item in enumerate(self.sidebar_items):
            frame = self.selection_boxes[i]
            cropped = self.previews[i]
            # Trim transparent pixels
            if self.bg_remove_enabled and self.bg_remove_color:
                cropped = self.remove_background(cropped, self.bg_remove_color)
            trimmed_img, bbox = trim_transparent(cropped)
            x1, y1, x2, y2 = frame
            left_trim, top_trim = bbox[0], bbox[1]
            final_x = x1 + left_trim
            final_y = y1 + top_trim
            final_w = bbox[2] - bbox[0]
            final_h = bbox[3] - bbox[1]

            base_name = item.name_entry.get().strip() or f"sprite_{i}"

            if item.is_animation.get():
                # Increment sequential number for this base name
                count = anim_counters.get(base_name, 0) + 1
                anim_counters[base_name] = count
                filename = f"splitani_{base_name}_{count}.png"
                metadata_name = f"splitani_{base_name}_{count}"
            else:
                filename = f"split_{base_name}.png"
                metadata_name = f"split_{base_name}"

            out_path = os.path.join(folder, filename)
            trimmed_img.save(out_path)

            # Save metadata relative to folder
            self.frames_meta[metadata_name] = {
                "frame": {"x": int(final_x), "y": int(final_y), "w": int(final_w), "h": int(final_h)},
                "source": os.path.basename(self.image_path),
                "file": os.path.join(folder, filename)
            }
            saved_count += 1

        # Move to next image
        self.current_index += 1
        messagebox.showinfo("Saved", f"Saved {saved_count} sprites from {os.path.basename(self.image_path)}")
        self.load_image()

    def map_sprites(self):
        """
        Map all selections into a single Phaser-ready JSON (append to existing if present).
        Static sprites go under 'static', animations under 'animations'.
        """
        json_path = r"C:\Users\ashvi\Documents\VS_Codes\HTML\Agrividya\Web\sprites.json"

        # Load existing JSON if it exists
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                data = json.load(f)
            static_meta = data.get("static", {})
            animations_meta = data.get("animations", {})
        else:
            static_meta = {}
            animations_meta = {}

        anim_counters = {}
        mapped_count = 0

        for i, item in enumerate(self.sidebar_items):
            frame = self.selection_boxes[i]
            cropped = self.previews[i]

            # Trim transparent pixels
            if self.bg_remove_enabled and self.bg_remove_color:
                cropped = self.remove_background(cropped, self.bg_remove_color)
            trimmed_img, bbox = trim_transparent(cropped)

            x1, y1, x2, y2 = frame
            left_trim, top_trim = bbox[0], bbox[1]
            final_x = x1 + left_trim
            final_y = y1 + top_trim
            final_w = bbox[2] - bbox[0]
            final_h = bbox[3] - bbox[1]

            base_name = item.name_entry.get().strip() or f"sprite_{i}"
            source_name = os.path.basename(self.image_path)

            if item.is_animation.get():
                count = anim_counters.get(base_name, 0) + 1
                anim_counters[base_name] = count
                frame_id = f"{base_name}_{count}"

                frame_data = {"x": int(final_x), "y": int(final_y), "w": int(final_w), "h": int(final_h), "source": source_name}

                # Store frame globally
                static_meta[frame_id] = frame_data

                # Add to animation sequence
                if base_name not in animations_meta:
                    animations_meta[base_name] = {"frames": [], "frameRate": 8, "loop": True}
                animations_meta[base_name]["frames"].append(frame_id)
            else:
                static_meta[base_name] = {"x": int(final_x), "y": int(final_y), "w": int(final_w), "h": int(final_h), "source": source_name}

            mapped_count += 1

        # Save back to JSON
        with open(json_path, "w") as f:
            json.dump({"static": static_meta, "animations": animations_meta}, f, indent=2)

        messagebox.showinfo("Mapped", f"Mapped {mapped_count} sprites from {os.path.basename(self.image_path)}")
        self.current_index += 1
        self.load_image()

    def skip(self):
        self.current_index += 1
        self.load_image()

    def finish(self):
        # Write aggregate JSON
        json_path = os.path.join("assets", "split_sprites.json")
        with open(json_path, "w") as f:
            json.dump({"frames": self.frames_meta}, f, indent=2)
        messagebox.showinfo("Done", f"✅ Saved total {len(self.frames_meta)} sprites. JSON: {json_path}")
        self.root.quit()

if __name__ == "__main__":
    # Single root usage: hide for file dialog then show.
    root = tk.Tk()
    root.withdraw()
    filetypes = [("Image files", "*.png;*.jpg;*.jpeg;*.bmp")]
    img_paths = filedialog.askopenfilenames(title="Select spritesheet images", filetypes=filetypes)
    if not img_paths:
        print("No images selected.")
        root.destroy()
    else:
        root.deiconify()
        app = SpriteExtractor(root, img_paths)
        root.mainloop()