from PIL import Image, ImageChops, ImageEnhance
import numpy as np

def create_gif(frames, filename, duration=200):
    # frames[0].save(filename, save_all=True, append_images=frames[1:], duration=duration, loop=0, disposal=2)
    # pillow gif saving with transparency can be tricky, let's process each frame
    processed = []
    for f in frames:
        # P mode with transparency
        alpha = f.split()[3]
        f = f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        mask = Image.eval(alpha, lambda a: 255 if a <=128 else 0)
        f.paste(255, mask)
        f.info['transparency'] = 255
        processed.append(f)
    processed[0].save(filename, save_all=True, append_images=processed[1:], duration=duration, loop=0, disposal=2)
    print(f"Saved {filename}")

img_path = 'avatar_transparent.png'
base_img = Image.open(img_path).convert("RGBA")
W, H = base_img.size

# --- 1. IDLING (Screen pulses / symbols animate) ---
print("Generating Idle Animation...")
# We will identify the screen by finding neon colors (cyan/green/magenta) on the left/center
data = np.array(base_img)
# A simple way to simulate screen animation is to create a mask of the brightest pixels in the cyan/green spectrum
# and shift them in a loop, or just modulate their brightness.
# Let's modulate brightness of highly saturated cyan/blue/green pixels
hsv = base_img.convert('HSV')
hsv_data = np.array(hsv)
# H (0-255), S (0-255), V (0-255)
screen_mask = (hsv_data[:,:,1] > 150) & (hsv_data[:,:,2] > 150) & (data[:,:,3] > 0)
# Also restrict to left-ish half and middle height for laptop screen
y_grid, x_grid = np.mgrid[0:H, 0:W]
screen_mask = screen_mask & (x_grid < W * 0.7) & (y_grid > H * 0.2) & (y_grid < H * 0.7)

idle_frames = []
for i in range(4):
    frame_data = data.copy()
    # Pulse the screen pixels
    pulse_factor = 0.7 + 0.3 * (i % 2) # Toggle brightness
    frame_data[screen_mask, :3] = np.clip(frame_data[screen_mask, :3] * pulse_factor, 0, 255)
    idle_frames.append(Image.fromarray(frame_data, "RGBA"))

create_gif(idle_frames, 'animations/avatar_idle.gif', duration=300)

# --- 2. TYPING ---
print("Generating Typing Animation...")
# Typing = Hands move up/down. Hands are usually near the bottom center.
# We'll mask out a rectangle in the middle-lower region and shift its pixels up/down + screen pulse.
cx, cy = int(W*0.5), int(H*0.7)
hand_box = (int(W*0.3), int(H*0.5), int(W*0.7), int(H*0.85)) # (left, top, right, bottom)
typing_frames = []
for i in range(4):
    f = idle_frames[i].copy() # keep screen animation
    # Shift hands block by a few pixels
    shift_y = 4 if i % 2 == 1 else 0
    if shift_y > 0:
        hand_img = base_img.crop(hand_box)
        # Clear original hand area (this might leave a hole, but we're just shifting slightly)
        # Shift down
        f.paste(hand_img, (hand_box[0], hand_box[1] + shift_y), hand_img)
    typing_frames.append(f)

create_gif(typing_frames, 'animations/avatar_typing.gif', duration=150)

# --- 3. DRINKING ---
print("Generating Drinking Animation...")
# Drink = Mug + right arm moves up to face.
# Mug is bottom right. Face is top center.
# We'll take a large chunk from the right side and literally rotate / translate it upwards and leftwards.
drink_frames = [base_img] # frame 0: rest
# Slice arm/mug
arm_box = (int(W*0.65), int(H*0.3), W, int(H*0.95))
arm_img = base_img.crop(arm_box)

# We need a frame of holding the cup up
drink_frame_2 = base_img.copy()
# Optional: blank out the arm region with transparent before pasting?
# In PIL, making a region transparent:
bg_clear = Image.new("RGBA", (arm_box[2]-arm_box[0], arm_box[3]-arm_box[1]), (0,0,0,0))
drink_frame_2.paste(bg_clear, arm_box)
# Now paste the arm translated up and left
drink_frame_2.paste(arm_img, (arm_box[0] - int(W*0.1), arm_box[1] - int(H*0.15)), arm_img)

drink_frames = [base_img, drink_frame_2, drink_frame_2, base_img]
create_gif(drink_frames, 'animations/avatar_drink.gif', duration=400)

