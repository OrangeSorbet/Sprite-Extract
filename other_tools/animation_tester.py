import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

# --- Global variables ---
animation_frames = []
animation_job = None
scale = 1.0  # zoom factor

def update_animation(label, frame_index):
    """Recursively updates the label with the next animation frame."""
    global animation_job
    try:
        frame = animation_frames[frame_index]
        label.config(image=frame)
        next_frame_index = (frame_index + 1) % len(animation_frames)
        animation_job = label.after(150, update_animation, label, next_frame_index)
    except IndexError:
        pass

def select_images_and_play():
    """Select images and display at original resolution with zoom support."""
    global animation_frames, animation_job, scale

    # Stop previous animation
    if animation_job:
        gif_canvas.after_cancel(animation_job)
        animation_job = None

    animation_frames.clear()
    gif_canvas.delete("all")
    
    file_paths = filedialog.askopenfilenames(
        title="Select Images",
        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")]
    )
    if not file_paths:
        return

    try:
        pil_images = [Image.open(fp).convert("RGBA") for fp in file_paths]

        # Create PhotoImage frames at original resolution
        for img in pil_images:
            tk_frame = ImageTk.PhotoImage(img)
            animation_frames.append(tk_frame)

    except Exception as e:
        print(f"Error loading images: {e}")
        return

    if animation_frames:
        update_animation(gif_label, 0)
        display_frame(0)

def display_frame(frame_index):
    """Display a frame on the canvas with current zoom."""
    gif_canvas.delete("all")
    frame = animation_frames[frame_index]
    w, h = frame.width(), frame.height()
    # Scale the image according to zoom
    gif_canvas_img = gif_canvas.create_image(0, 0, anchor="nw", image=frame)
    gif_canvas.image_ref = frame
    gif_canvas.config(scrollregion=(0, 0, int(w*scale), int(h*scale)))

def zoom(event):
    """Zoom in/out with mouse wheel."""
    global scale
    if event.delta > 0:
        scale *= 1.1
    else:
        scale /= 1.1
    scale = max(0.1, min(scale, 10))  # limit zoom between 10% and 1000%
    gif_canvas.scale("all", 0, 0, scale, scale)
    gif_canvas.configure(scrollregion=gif_canvas.bbox("all"))

# --- GUI Setup ---
root = tk.Tk()
root.title("Original Resolution GIF Viewer")
root.geometry("800x600")

# Canvas with scrollbars
gif_canvas = tk.Canvas(root, bg="black")
gif_canvas.pack(fill="both", expand=True, side="left")

hbar = tk.Scrollbar(root, orient="horizontal", command=gif_canvas.xview)
hbar.pack(side="bottom", fill="x")
vbar = tk.Scrollbar(root, orient="vertical", command=gif_canvas.yview)
vbar.pack(side="right", fill="y")

gif_canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

# Bind zoom to Ctrl + MouseWheel
gif_canvas.bind("<Control-MouseWheel>", zoom)

# Label for animation overlay
gif_label = tk.Label(gif_canvas, bg="black")
gif_label.place(x=0, y=0)

# Button to load images
select_button = tk.Button(root, text="Select Images", command=select_images_and_play)
select_button.pack(pady=5, side="top")

root.mainloop()
