# Sprite Extractor

# Features
- Select multiple images, open one-by-one
- Draw rectangles to select sprites
- Sidebar shows thumbnail, name box, animation toggle, order label, delete button
- Drag sidebar items to reorder
- Save trims transparent pixels, saves PNGs, writes JSON metadata

# Prerequisites
- Python 3.13.7 must be installed

# Setup
python -m venv .venv
Windows
```
.venv/Scripts/activate
```
macOS/Linux
```
source .venv/bin/activate
```
```
pip install --upgrade pip
pip install pillow tkinterdnd2 pycryptodome
```

# Running the App
`python sprite_extractor.py`

# Features (v1.0.0)
- Select multiple images, which open one-by-one for processing
- Draw rectangles on images to select individual sprites
- Sidebar displays each selection with:
  - Thumbnail preview
  - Name entry box
  - Animation toggle checkbox
  - Order label showing sequence number
  - Delete button to remove the sprite
- Drag and reorder sidebar items; animation order updates automatically
- Snap selections to a configurable grid for precise alignment
- Show visual grid with selectable sizes (8x8, 16x16, 32x32, 64x64)
- Undo and redo actions for selection adjustments
- Background color picker to remove a uniform background from sprites
- Auto-detect sprites separated by transparency or chosen background color
- Zoom in/out with Ctrl + MouseWheel
- Move image with arrow keys for fine adjustments
- Save selections with transparent pixel trimming
- Save individual sprites as PNG files with proper naming conventions
- Generate metadata JSON (assets/split_sprites.json) with frame details
- Map all selections into a Phaser-ready JSON for static and animation frames
- Skip images or cancel processing at any time

# v2.0.0

- Undo and redo selection changes.  
- Background remover with color picking and auto-removal.  
- Auto-detect sprites separated by transparency or chosen background color.  
- Zoom in/out using Ctrl + MouseWheel.  
- Move image on canvas with arrow keys for fine adjustments.  
- Sidebar scrollable to accommodate large numbers of sprites.  
- Canvas background color toggle: black or white.  
- Instructions panel inside the UI for user guidance.  
- Handles fullscreen mode and responsive canvas resizing.  
- Grid numbers displayed dynamically while drawing selection rectangles.  
- "Map & Next" button to generate Phaser-ready JSON for static and animated frames.  