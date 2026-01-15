import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image

def create_gif():
    # Select input images
    file_paths = filedialog.askopenfilenames(
        title="Select Images for GIF",
        filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
    )
    if not file_paths:
        return

    # Select output file
    out_path = filedialog.asksaveasfilename(
        title="Save GIF As",
        defaultextension=".gif",
        filetypes=[("GIF files", "*.gif")]
    )
    if not out_path:
        return

    try:
        # Open all images
        pil_images = [Image.open(fp).convert("RGBA") for fp in file_paths]

        # Find max width/height to standardize canvas size
        max_w = max(img.width for img in pil_images)
        max_h = max(img.height for img in pil_images)

        frames = []
        for img in pil_images:
            # Create transparent canvas
            canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
            # Paste at bottom center
            x = (max_w - img.width) // 2
            y = max_h - img.height
            canvas.paste(img, (x, y), img)

            # Convert to palette while keeping transparency
            p_img = canvas.convert("P", palette=Image.ADAPTIVE)
            # Force transparency index
            mask = canvas.getchannel("A")  # alpha channel
            p_img.info["transparency"] = p_img.getpixel((0, 0))  # pick top-left transparent pixel
            frames.append(p_img)

        # Save as GIF with transparency + disposal
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=150,
            loop=0,
            disposal=2,
            transparency=frames[0].info["transparency"]
        )

        messagebox.showinfo("Success", f"GIF saved at:\n{out_path}")

    except Exception as e:
        messagebox.showerror("Error", str(e))

# --- GUI ---
root = tk.Tk()
root.title("Image to GIF Converter")
root.geometry("300x100")

btn = tk.Button(root, text="Select Images → Save GIF", command=create_gif)
btn.pack(expand=True, pady=20)

root.mainloop()
