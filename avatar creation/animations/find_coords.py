from PIL import Image, ImageDraw
import sys

img_path = 'avatar_transparent.png'
img = Image.open(img_path).convert("RGBA")

# Let's draw some boxes to guess coordinates
print(f"Size: {img.size}")

# Find cyan pixels
pixels = img.load()
cyan_min_y, cyan_max_y = 10000, 0
cyan_min_x, cyan_max_x = 10000, 0

for y in range(img.height):
    for x in range(img.width):
        r, g, b, a = pixels[x, y]
        # Cyan is roughly R<100, G>200, B>200, considering generated pixel art might have different hues, try a looser bound
        if a > 0 and r < 120 and g > 150 and b > 150:
            cyan_min_x = min(cyan_min_x, x)
            cyan_max_x = max(cyan_max_x, x)
            cyan_min_y = min(cyan_min_y, y)
            cyan_max_y = max(cyan_max_y, y)

print(f"Cyan/Screen area guess: ({cyan_min_x}, {cyan_min_y}) to ({cyan_max_x}, {cyan_max_y})")

