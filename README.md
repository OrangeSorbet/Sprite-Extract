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
- Map all selections for static and animation frames
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

# v3.0.0 (beta)

- Sticker editor popup for per-sprite editing before saving  
- Brush-based transparency removal and restoration  
- Adjustable border color and thickness for sprites  
- Background color picker with smart removal  
- Automatic sprite detection from transparency or background color  
- Undo and redo support for selections and edits  
- Grid-number overlay for precise selection sizing  
- One-click toggle for animation mode on all sprites  
- Smooth mouse-wheel scrolling in the sidebar  
- Canvas background toggle between black and white  
- Fullscreen responsive layout with auto-resizing  
- Keyboard nudging for fine image alignment  
- Ctrl + mouse wheel zoom centered on cursor  
- Improved auto-naming for detected sprites  
- Persistent sticker editor settings between edits  
- Updated in-app instructions for advanced features  