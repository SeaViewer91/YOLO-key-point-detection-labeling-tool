
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import os
import glob
import sys

# Configuration
# This tool saves variable number of keypoints.
# Ensure you click keypoints in the consistent order required by your model topology.

class KeypointLabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("YOLO Keypoint Labeling Tool")
        self.root.geometry("1400x900")

        # State Variables
        self.image_dir = ""
        self.image_list = []
        self.current_image_index = 0
        self.current_image_path = None
        
        self.original_image = None  # PIL Image
        self.display_image = None   # PIL Image for display
        self.tk_image = None        # ImageTk object
        
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.labels = [] # List of dicts: {'bbox': [x1, y1, x2, y2], 'keypoints': [(x, y, v), ...], 'class_id': 0}
        self.selected_object_index = -1
        
        self.class_id = 0
        self.keypoint_visibility = 2 

        # UI Layout
        self.setup_ui()
        
        # Events
        self.canvas.bind("<ButtonPress-1>", self.on_left_down)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
        
        self.canvas.bind("<ButtonPress-3>", self.on_right_click) # Right click to add keypoint
        
        self.canvas.bind("<MouseWheel>", self.on_wheel) # Windows Zoom
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start) # Middle click pan
        self.canvas.bind("<B2-Motion>", self.on_pan_drag)
        
        # Linux scroll support
        self.canvas.bind("<Button-4>", self.on_wheel)
        self.canvas.bind("<Button-5>", self.on_wheel)

        self.root.bind("<Left>", self.prev_image)
        self.root.bind("<Right>", self.next_image)
        self.root.bind("<Delete>", self.delete_selected)
        self.root.bind("<BackSpace>", self.delete_last_keypoint) # New feature
        self.root.bind("<Control-s>", lambda e: self.save_labels())

    def setup_ui(self):
        # Toolbar
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        btn_open = tk.Button(toolbar, text="Open Dir", command=self.open_dir)
        btn_open.pack(side=tk.LEFT, padx=5, pady=5)
        
        btn_prev = tk.Button(toolbar, text="<< Prev (Left)", command=self.prev_image)
        btn_prev.pack(side=tk.LEFT, padx=5)
        
        btn_next = tk.Button(toolbar, text="Next >> (Right)", command=self.next_image)
        btn_next.pack(side=tk.LEFT, padx=5)
        
        btn_save = tk.Button(toolbar, text="Save (Ctrl+S)", command=self.save_labels)
        btn_save.pack(side=tk.LEFT, padx=5)
        
        btn_del = tk.Button(toolbar, text="Del Object (Del)", command=self.delete_selected)
        btn_del.pack(side=tk.LEFT, padx=5)

        btn_del_kp = tk.Button(toolbar, text="Del Last KP (Bksp)", command=self.delete_last_keypoint)
        btn_del_kp.pack(side=tk.LEFT, padx=5)
        
        tk.Label(toolbar, text="Class ID:").pack(side=tk.LEFT, padx=5)
        self.entry_class = tk.Entry(toolbar, width=5)
        self.entry_class.insert(0, "0")
        self.entry_class.pack(side=tk.LEFT)
        self.entry_class.bind("<KeyRelease>", self.update_class_id)

        # Instructions
        self.info_label = tk.Label(toolbar, text="Load a directory to start")
        self.info_label.pack(side=tk.RIGHT, padx=10)

        # Main Area
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#333333", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Help Text overlay
        help_text = "Controls:\nMouse Wheel: Zoom\nMiddle Drag: Pan\nLeft Drag: Create Box\nLeft Click: Select Box\nRight Click: Add Keypoint\nDel: Delete Object\nBackspace: Delete Last Keypoint"
        self.canvas.create_text(10, 10, text=help_text, anchor=tk.NW, fill="white", tags="help")

    def update_class_id(self, event):
        try:
            self.class_id = int(self.entry_class.get())
        except ValueError:
            pass

    def open_dir(self):
        directory = filedialog.askdirectory()
        if not directory:
            return
        self.image_dir = directory
        # Extensions
        exts = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        self.image_list = []
        for ext in exts:
            self.image_list.extend(glob.glob(os.path.join(directory, ext)))
            self.image_list.extend(glob.glob(os.path.join(directory, ext.upper())))
        
        self.image_list = sorted(list(set(self.image_list)))
        
        if not self.image_list:
            messagebox.showinfo("Info", "No images found in directory.")
            return
            
        self.current_image_index = 0
        self.load_image()

    def load_image(self):
        if not self.image_list:
            return
            
        path = self.image_list[self.current_image_index]
        self.current_image_path = path # Full path
        
        try:
            self.original_image = Image.open(path)
        except Exception as e:
            print(f"Failed to open image: {e}")
            return

        # Reset View
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Load Labels
        self.load_labels()
        
        self.draw_image()
        self.info_label.config(text=f"[{self.current_image_index+1}/{len(self.image_list)}] {os.path.basename(path)}")
    
    def load_labels(self):
        self.labels = []
        self.selected_object_index = -1
        
        txt_path = os.path.splitext(self.current_image_path)[0] + ".txt"
        if os.path.exists(txt_path):
            try:
                with open(txt_path, 'r') as f:
                    lines = f.readlines()
                    
                w, h = self.original_image.size
                
                for line in lines:
                    parts = list(map(float, line.strip().split()))
                    if len(parts) < 5: continue
                    
                    c_id = int(parts[0])
                    x_c, y_c, bw, bh = parts[1:5]
                    
                    # Convert to pixel coords
                    abs_w = bw * w
                    abs_h = bh * h
                    abs_x = (x_c * w) - (abs_w / 2)
                    abs_y = (y_c * h) - (abs_h / 2)
                    
                    bbox = [abs_x, abs_y, abs_x + abs_w, abs_y + abs_h]
                    
                    # Keypoints
                    kps = []
                    kp_data = parts[5:]
                    
                    # Autodetect format: x,y,v (3) or x,y (2)
                    has_vis = True
                    step = 3
                    if len(kp_data) > 0:
                        # Heuristic: if divisible by 3, assume 3. If mixed, tricky.
                        # Usually consistent.
                        if len(kp_data) % 3 != 0 and len(kp_data) % 2 == 0:
                            step = 2
                            has_vis = False
                    
                    for i in range(0, len(kp_data), step):
                        kx_n = kp_data[i]
                        ky_n = kp_data[i+1]
                        kv = 2
                        if step == 3:
                            kv = int(kp_data[i+2])
                        
                        kx = kx_n * w
                        ky = ky_n * h
                        kps.append([kx, ky, kv])
                        
                    self.labels.append({
                        'class_id': c_id,
                        'bbox': bbox,
                        'keypoints': kps
                    })
            except Exception as e:
                print(f"Error loading labels: {e}")

    def save_labels(self):
        if not self.current_image_path or not self.original_image:
            return

        txt_path = os.path.splitext(self.current_image_path)[0] + ".txt"
        w, h = self.original_image.size
        
        lines = []
        for obj in self.labels:
            c_id = obj['class_id']
            bbox = obj['bbox']
            # Normalize bbox
            # x_center, y_center, width, height
            abs_w = bbox[2] - bbox[0]
            abs_h = bbox[3] - bbox[1]
            abs_cx = bbox[0] + abs_w / 2
            abs_cy = bbox[1] + abs_h / 2
            
            n_cx = abs_cx / w
            n_cy = abs_cy / h
            n_w = abs_w / w
            n_h = abs_h / h
            
            # Format: class xc yc w h p1x p1y p1v ...
            line_parts = [f"{c_id}", f"{n_cx:.6f}", f"{n_cy:.6f}", f"{n_w:.6f}", f"{n_h:.6f}"]
            
            for kp in obj['keypoints']:
                # Normalize keypoints
                nkx = kp[0] / w
                nky = kp[1] / h
                nv = kp[2]
                line_parts.extend([f"{nkx:.6f}", f"{nky:.6f}", f"{nv}"])
            
            lines.append(" ".join(line_parts))
            
        with open(txt_path, 'w') as f:
            f.write("\n".join(lines))
        
        # Feedback
        self.canvas.delete("save_msg")
        self.canvas.create_text(self.canvas.winfo_width()/2, 30, text="Saved!", fill="#00ff00", font=("Arial", 20, "bold"), tags="save_msg")
        self.root.after(1000, lambda: self.canvas.delete("save_msg"))

    def prev_image(self, event=None):
        if self.current_image_index > 0:
            self.save_labels() # Auto save
            self.current_image_index -= 1
            self.load_image()
            
    def next_image(self, event=None):
        if self.current_image_index < len(self.image_list) - 1:
            self.save_labels() # Auto save
            self.current_image_index += 1
            self.load_image()

    def draw_image(self):
        if not self.original_image:
            return
            
        w_can = self.canvas.winfo_width()
        h_can = self.canvas.winfo_height()
        if w_can <= 1: w_can = 800
        if h_can <= 1: h_can = 600
        
        nw, nh = int(self.original_image.width * self.scale), int(self.original_image.height * self.scale)
        if nw < 1 or nh < 1: return
        
        # Optimization: only resize if reasonably small or if PIL handled efficient crop
        # For simplicity, we resize whole image then serve it.
        # Note: If memory usage is high for huge images, we need cropping.
        
        try:
            final_img = self.original_image.resize((nw, nh), Image.Resampling.BILINEAR)
            self.tk_image = ImageTk.PhotoImage(final_img)
            
            self.canvas.delete("all")
            self.canvas.create_image(self.offset_x, self.offset_y, image=self.tk_image, anchor=tk.NW, tags="img")
        except Exception as e:
            print(e)
            return

        self.draw_labels()
        
        # Re-draw help text
        help_text = "Controls:\nMouse Wheel: Zoom\nMiddle Drag: Pan\nLeft Drag: Create Box\nLeft Click: Select Box\nRight Click: Add Keypoint\nDel: Delete Object\nBackspace: Delete Last Keypoint"
        self.canvas.create_text(10, 10, text=help_text, anchor=tk.NW, fill="yellow", tags="help")

    def draw_labels(self):
        for idx, obj in enumerate(self.labels):
            bbox = obj['bbox']
            kps = obj['keypoints']
            
            # Transform to screen coords
            x1, y1, x2, y2 = bbox
            sx1 = x1 * self.scale + self.offset_x
            sy1 = y1 * self.scale + self.offset_y
            sx2 = x2 * self.scale + self.offset_x
            sy2 = y2 * self.scale + self.offset_y
            
            color = "cyan" if idx == self.selected_object_index else "red"
            width = 3 if idx == self.selected_object_index else 2
            
            # Draw Box
            self.canvas.create_rectangle(sx1, sy1, sx2, sy2, outline=color, width=width, tags=f"box_{idx}")
            self.canvas.create_text(sx1, sy1-15, text=f"ID:{idx} C:{obj['class_id']}", fill=color, anchor=tk.NW, font=("Arial", 10, "bold"))
            
            # Draw Keypoints
            prev_skx, prev_sky = None, None
            for i, kp in enumerate(kps):
                kx, ky, kv = kp
                skx = kx * self.scale + self.offset_x
                sky = ky * self.scale + self.offset_y
                
                kp_color = "yellow" if idx == self.selected_object_index else "#00ff00"
                r = 4
                self.canvas.create_oval(skx-r, sky-r, skx+r, sky+r, fill=kp_color, outline="black", tags=f"kp_{idx}_{i}")
                
                # Show index
                self.canvas.create_text(skx+5, sky+5, text=str(i+1), fill="white", font=("Arial", 8))
                
                # Draw skeleton lines (sequential)
                if prev_skx is not None:
                     self.canvas.create_line(prev_skx, prev_sky, skx, sky, fill=color, width=1)
                prev_skx, prev_sky = skx, sky

    def screen_to_image(self, sx, sy):
        ix = (sx - self.offset_x) / self.scale
        iy = (sy - self.offset_y) / self.scale
        return ix, iy

    def on_left_down(self, event):
        ix, iy = self.screen_to_image(event.x, event.y)
        
        # Check if clicking on existing box? (Selection)
        clicked_index = -1
        # Check in reverse order (topmost first)
        for idx in range(len(self.labels)-1, -1, -1):
            x1, y1, x2, y2 = self.labels[idx]['bbox']
            # Simple hit test on bbox
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                clicked_index = idx
                break
        
        if clicked_index != -1:
            self.selected_object_index = clicked_index
            self.drag_start = None
            self.draw_image()
            return

        # Note: If no box clicked, start drawing new box
        self.selected_object_index = -1
        self.draw_image()
        self.drag_start = (ix, iy)
        self.cur_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="green", width=2, tags="temp_rect")

    def on_left_drag(self, event):
        if hasattr(self, 'drag_start') and self.drag_start:
            # Updating temp rect
            start_ix, start_iy = self.drag_start
            
            sx1 = start_ix * self.scale + self.offset_x
            sy1 = start_iy * self.scale + self.offset_y
            
            self.canvas.coords("temp_rect", sx1, sy1, event.x, event.y)

    def on_left_up(self, event):
        if hasattr(self, 'drag_start') and self.drag_start:
            ix, iy = self.screen_to_image(event.x, event.y)
            start_x, start_y = self.drag_start
            
            x1, x2 = sorted([start_x, ix])
            y1, y2 = sorted([start_y, iy])
            
            if (x2 - x1) > 5 and (y2 - y1) > 5:
                new_obj = {
                    'class_id': self.class_id,
                    'bbox': [x1, y1, x2, y2],
                    'keypoints': []
                }
                self.labels.append(new_obj)
                self.selected_object_index = len(self.labels) - 1
                
            self.canvas.delete("temp_rect")
            self.drag_start = None
            self.draw_image()

    def on_right_click(self, event):
        if self.selected_object_index != -1 and 0 <= self.selected_object_index < len(self.labels):
            ix, iy = self.screen_to_image(event.x, event.y)
            # Add keypoint
            self.labels[self.selected_object_index]['keypoints'].append([ix, iy, 2])
            self.draw_image()

    def delete_selected(self, event=None):
        if self.selected_object_index != -1 and 0 <= self.selected_object_index < len(self.labels):
            del self.labels[self.selected_object_index]
            self.selected_object_index = -1
            self.draw_image()

    def delete_last_keypoint(self, event=None):
        if self.selected_object_index != -1 and 0 <= self.selected_object_index < len(self.labels):
            kps = self.labels[self.selected_object_index]['keypoints']
            if kps:
                kps.pop()
                self.draw_image()

    def on_wheel(self, event):
        old_scale = self.scale
        
        # Windows/Linux check
        if event.num == 5 or event.delta < 0:
            scale_factor = 0.9
        else:
            scale_factor = 1.1
            
        new_scale = old_scale * scale_factor
        if new_scale < 0.1: new_scale = 0.1
        if new_scale > 20: new_scale = 20
        
        self.scale = new_scale
        
        mouse_x = event.x
        mouse_y = event.y
        
        self.offset_x = mouse_x - (mouse_x - self.offset_x) * (new_scale / old_scale)
        self.offset_y = mouse_y - (mouse_y - self.offset_y) * (new_scale / old_scale)
        
        self.draw_image()

    def on_pan_start(self, event):
        self.pan_start = (event.x, event.y)
        self.pan_start_offset = (self.offset_x, self.offset_y)

    def on_pan_drag(self, event):
        if hasattr(self, 'pan_start'):
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.offset_x = self.pan_start_offset[0] + dx
            self.offset_y = self.pan_start_offset[1] + dy
            self.draw_image()

if __name__ == "__main__":
    root = tk.Tk()
    app = KeypointLabeler(root)
    root.mainloop()
