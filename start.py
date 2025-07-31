import tkinter as tk
from tkinter import ttk
from decimal import Decimal, getcontext
import secp256k1 as ice
import math
import random

# Set high precision for decimal calculations
getcontext().prec = 100
target = '12VVRNPi4SJqUTsp6FmqDqY5sGosDtysn4'

def shuffle_string(s):
    char_list = list(s)
    random.shuffle(char_list)
    return ''.join(char_list)
    
def rotate_hex(hex_string):
    # Precompute a translation table for all hex digits
    translation_table = str.maketrans("0123456789abcdef", "123456789abcdef0")
    return hex_string.translate(translation_table)

def shift_left(s, n):
    n = n % len(s)
    return s[n:] + s[:n]

def inverse(binary_string):
    # Ensure the input is valid
    if not all(char in '01' for char in binary_string):
        raise ValueError("Input string must contain only '0' and '1'")
    
    return ''.join('1' if char == '0' else '0' for char in binary_string)

class HexRangeExplorer:
    def __init__(self, root):
        self.root = root
        self.root.title("Hex Range Explorer")
        
        # Define the range using Decimal for precise calculations
        self.range_start = 0x1000000000000000000
        self.range_end = 0x1ffffffffffffffffff
        self.range_size = self.range_end - self.range_start + 1
        
        # Use Decimal for precise position tracking
        self.range_start_dec = Decimal(self.range_start)
        self.range_end_dec = Decimal(self.range_end)
        self.range_size_dec = Decimal(self.range_size)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create canvas
        self.canvas_width = 800
        self.canvas_height = 600
        self.canvas = tk.Canvas(main_frame, width=self.canvas_width, 
                               height=self.canvas_height, bg='black')
        self.canvas.grid(row=0, column=0, columnspan=2)
        
        # Create info labels with monospace font for better hex display
        font_mono = ('Courier', 10)
        
        self.position_label = ttk.Label(main_frame, text="Position: ", font=font_mono)
        self.position_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.hex_label = ttk.Label(main_frame, text="Hex: ", font=font_mono)
        self.hex_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.decimal_label = ttk.Label(main_frame, text="Decimal: ", font=font_mono)
        self.decimal_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.zoom_info_label = ttk.Label(main_frame, text="Zoom: 1x", font=font_mono)
        self.zoom_info_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        
        # Auto-scroll controls
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.auto_scroll_enabled = False
        self.auto_scroll_speed = 1.0  # pixels per frame
        self.auto_scroll_direction = 1  # 1 for right, -1 for left
        self.random_mode = False  # Random walk mode
        self.random_change_interval = 30  # Frames before changing direction
        self.random_frame_count = 0
        self.random_target_x = self.canvas_width // 2
        self.random_velocity_x = 0
        self.random_zoom_target = 1.0  # Target zoom level
        self.random_zoom_velocity = 0  # Zoom velocity
        
        self.auto_button = ttk.Button(control_frame, text="Start Auto-Scroll", 
                                     command=self.toggle_auto_scroll)
        self.auto_button.grid(row=0, column=0, padx=5)
        
        self.random_button = ttk.Button(control_frame, text="Random Mode: OFF", 
                                       command=self.toggle_random_mode)
        self.random_button.grid(row=0, column=1, padx=5)
        
        ttk.Label(control_frame, text="Speed:", font=font_mono).grid(row=0, column=2, padx=5)
        
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = ttk.Scale(control_frame, from_=0.1, to=10.0, 
                                    orient=tk.HORIZONTAL, variable=self.speed_var,
                                    command=self.update_speed, length=200)
        self.speed_scale.grid(row=0, column=3, padx=5)
        
        self.speed_label = ttk.Label(control_frame, text="1.0x", font=font_mono)
        self.speed_label.grid(row=0, column=4, padx=5)
        
        self.direction_button = ttk.Button(control_frame, text="Direction: →", 
                                          command=self.toggle_direction)
        self.direction_button.grid(row=0, column=5, padx=5)
        
        # Precise viewport tracking using Decimal
        self.viewport_start = Decimal(self.range_start)
        self.viewport_end = Decimal(self.range_end)
        
        # Bind mouse events - fix platform-specific bindings
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        # Platform-specific mouse wheel bindings
        # Windows and MacOS
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        # Linux
        self.canvas.bind("<Button-4>", self.on_mouse_wheel_linux_up)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel_linux_down)
        
        # Keyboard bindings for auto-scroll control
        root.bind("<space>", lambda e: self.toggle_auto_scroll())
        root.bind("<Left>", lambda e: self.set_direction(-1) if not self.random_mode else None)
        root.bind("<Right>", lambda e: self.set_direction(1) if not self.random_mode else None)
        root.bind("<Up>", lambda e: self.increase_speed())
        root.bind("<Down>", lambda e: self.decrease_speed())
        root.bind("<r>", lambda e: self.toggle_random_mode())
        
        # Focus canvas to receive events
        self.canvas.focus_set()
        
        # For dragging
        self.drag_start_x = None
        self.drag_start_viewport = None
        
        # Store last mouse position
        self.last_mouse_x = self.canvas_width // 2
        
        # Draw initial display
        self.draw_display()
        
    def toggle_auto_scroll(self):
        """Toggle automatic scrolling on/off"""
        self.auto_scroll_enabled = not self.auto_scroll_enabled
        if self.auto_scroll_enabled:
            self.auto_button.config(text="Stop Auto-Scroll")
            self.auto_scroll()
        else:
            self.auto_button.config(text="Start Auto-Scroll")
    
    def toggle_direction(self):
        """Toggle scroll direction"""
        self.auto_scroll_direction *= -1
        if self.auto_scroll_direction > 0:
            self.direction_button.config(text="Direction: →")
        else:
            self.direction_button.config(text="Direction: ←")
    
    def update_speed(self, value):
        """Update scroll speed from slider"""
        self.auto_scroll_speed = float(value)
        self.speed_label.config(text=f"{self.auto_scroll_speed:.1f}x")
    
    def toggle_random_mode(self):
        """Toggle random walk mode"""
        self.random_mode = not self.random_mode
        if self.random_mode:
            self.random_button.config(text="Random Mode: ON")
            self.direction_button.config(state='disabled')
            # Initialize random movement
            self.random_target_x = random.randint(0, self.canvas_width)
            self.random_velocity_x = 0
        else:
            self.random_button.config(text="Random Mode: OFF")
            self.direction_button.config(state='normal')
    
    def auto_scroll(self):
        """Perform automatic scrolling"""
        if not self.auto_scroll_enabled:
            return
        
        if self.random_mode:
            # Random walk mode
            self.random_frame_count += 1
            
            # Change target occasionally or when reached
            if self.random_frame_count >= self.random_change_interval or abs(self.random_target_x - self.last_mouse_x) < 5:
                self.random_frame_count = 0
                self.random_change_interval = random.randint(20, 60)  # Vary the interval
                
                # Choose new random target position
                self.random_target_x = random.randint(0, self.canvas_width)
                
                # Also change zoom target occasionally
                if random.random() < 0.3:  # 30% chance to change zoom
                    current_zoom = float(self.range_size_dec / (self.viewport_end - self.viewport_start))
                    # Random zoom between 0.5x and 100000x on logarithmic scale
                    log_min = math.log10(0.5)
                    log_max = math.log10(100000)
                    log_target = random.uniform(log_min, log_max)
                    self.random_zoom_target = 10 ** log_target
                
                # Occasionally do a random jump in the viewport
                if random.random() < 0.1:  # 10% chance
                    # Random jump to a different part of the range
                    jump_factor = random.uniform(-0.5, 0.5)
                    viewport_size = self.viewport_end - self.viewport_start
                    jump_amount = viewport_size * Decimal(jump_factor)
                    
                    new_start = self.viewport_start + jump_amount
                    new_end = self.viewport_end + jump_amount
                    
                    # Clamp to valid range
                    if new_start < self.range_start_dec:
                        new_end = new_end + (self.range_start_dec - new_start)
                        new_start = self.range_start_dec
                    elif new_end > self.range_end_dec:
                        new_start = new_start - (new_end - self.range_end_dec)
                        new_end = self.range_end_dec
                    
                    self.viewport_start = new_start
                    self.viewport_end = new_end
            
            # Handle random zooming
            current_zoom = float(self.range_size_dec / (self.viewport_end - self.viewport_start))
            zoom_diff = math.log10(self.random_zoom_target / current_zoom)
            self.random_zoom_velocity += zoom_diff * 0.05  # Acceleration
            self.random_zoom_velocity *= 0.9  # Damping
            
            # Apply zoom change
            if abs(self.random_zoom_velocity) > 0.001:
                zoom_factor = 1.0 - (self.random_zoom_velocity * 0.02 * self.auto_scroll_speed)
                zoom_factor = max(0.95, min(1.05, zoom_factor))  # Limit zoom speed
                
                # Get value at current position before zoom
                current_x = int(self.last_mouse_x)
                value_under_cursor = Decimal(self.get_value_at_position(current_x))
                
                # Apply zoom
                mouse_fraction = Decimal(current_x) / Decimal(self.canvas_width)
                old_size = self.viewport_end - self.viewport_start
                new_size = old_size * Decimal(zoom_factor)
                
                # Limit size
                if new_size < 1:
                    new_size = Decimal('1')
                if new_size > self.range_size_dec:
                    new_size = self.range_size_dec
                
                # Calculate new viewport
                new_start = value_under_cursor - mouse_fraction * new_size
                new_end = new_start + new_size
                
                # Adjust if outside bounds
                if new_start < self.range_start_dec:
                    new_end = new_end + (self.range_start_dec - new_start)
                    new_start = self.range_start_dec
                elif new_end > self.range_end_dec:
                    new_start = new_start - (new_end - self.range_end_dec)
                    new_end = self.range_end_dec
                
                self.viewport_start = new_start
                self.viewport_end = new_end
                
                # Redraw when zoom changes
                self.draw_display()
                self.update_zoom_info()
            
            # Smooth movement towards target
            diff = self.random_target_x - self.last_mouse_x
            self.random_velocity_x += diff * 0.1  # Acceleration
            self.random_velocity_x *= 0.9  # Damping
            
            # Apply velocity with speed scaling
            move_x = self.random_velocity_x * self.auto_scroll_speed * 0.1
            new_x = self.last_mouse_x + move_x
            
            # Keep within bounds
            new_x = max(0, min(self.canvas_width, new_x))
            
            # Create synthetic mouse event for the new position
            event = type('obj', (object,), {'x': int(new_x), 'y': self.canvas_height // 2})
            
            # Process the value at this position
            value = self.get_value_at_position(int(new_x))
            self.process_hex_value(value)
            
            # Update position for next frame
            self.last_mouse_x = int(new_x)
            
            # Update display
            self.position_label.config(text=f"Position: ({int(new_x)}, {self.canvas_height // 2})")
            self.hex_label.config(text=f"Hex: 0x{value:x}")
            self.decimal_label.config(text=f"Decimal: {value:,}")
            
            # Draw crosshair at current position
            self.canvas.delete("crosshair")
            self.canvas.create_line(int(new_x), 0, int(new_x), self.canvas_height - 40,
                                  fill='red', width=2, tags="crosshair")
            self.canvas.create_rectangle(int(new_x) - 3, self.canvas_height - 40,
                                       int(new_x) + 3, self.canvas_height,
                                       fill='red', tags="crosshair")
            
        else:
            # Original linear scrolling mode
            viewport_size = self.viewport_end - self.viewport_start
            scroll_amount = (viewport_size / Decimal(self.canvas_width)) * Decimal(self.auto_scroll_speed) * Decimal(self.auto_scroll_direction)
            
            new_start = self.viewport_start + scroll_amount
            new_end = self.viewport_end + scroll_amount
            
            if new_start < self.range_start_dec:
                new_start = self.range_start_dec
                new_end = new_start + viewport_size
                self.auto_scroll_direction = 1
                self.direction_button.config(text="Direction: →")
            elif new_end > self.range_end_dec:
                new_end = self.range_end_dec
                new_start = new_end - viewport_size
                self.auto_scroll_direction = -1
                self.direction_button.config(text="Direction: ←")
            
            self.viewport_start = new_start
            self.viewport_end = new_end
            
            self.draw_display()
            self.update_zoom_info()
            
            center_x = self.canvas_width // 2
            center_value = self.get_value_at_position(center_x)
            self.process_hex_value(center_value)
            
            self.canvas.delete("crosshair")
            self.canvas.create_line(center_x, 0, center_x, self.canvas_height - 40,
                                  fill='yellow', width=2, tags="crosshair")
            self.canvas.create_rectangle(center_x - 2, self.canvas_height - 40,
                                       center_x + 2, self.canvas_height,
                                       fill='yellow', tags="crosshair")
        
        # Schedule next frame
        self.root.after(10, self.auto_scroll)
    
    def get_color_for_value(self, value, zoom_level):
        """Get color based on value and zoom level"""
        # Normalize value to 0-1 range
        norm_value = float((Decimal(value) - self.range_start_dec) / self.range_size_dec)
        
        # At high zoom levels, show bit patterns
        if zoom_level > 1000000:
            # Show individual bits as alternating patterns
            bit_pattern = value & 0xFF  # Look at lower 8 bits
            brightness = 50 + (bit_pattern * 205 // 255)
            
            # Create patterns based on bit positions
            r = brightness if (value & 0x1) else brightness // 2
            g = brightness if (value & 0x10) else brightness // 2
            b = brightness if (value & 0x100) else brightness // 2
            
        # At medium zoom levels, show byte boundaries
        elif zoom_level > 10000:
            # Color based on byte values
            byte_val = (value >> 8) & 0xFF
            hue = (byte_val / 255.0) * 360
            r, g, b = self.hsv_to_rgb(hue, 0.8, 0.9)
            
        # At low zoom levels, show smooth gradient
        else:
            # Smooth gradient with multiple color stops
            if norm_value < 0.25:
                # Blue to Cyan
                r = 0
                g = int(255 * (norm_value * 4))
                b = 255
            elif norm_value < 0.5:
                # Cyan to Green
                r = 0
                g = 255
                b = int(255 * (1 - (norm_value - 0.25) * 4))
            elif norm_value < 0.75:
                # Green to Yellow
                r = int(255 * ((norm_value - 0.5) * 4))
                g = 255
                b = 0
            else:
                # Yellow to Red
                r = 255
                g = int(255 * (1 - (norm_value - 0.75) * 4))
                b = 0
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB"""
        h = h / 360.0
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        
        i = i % 6
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
            
        return int(r * 255), int(g * 255), int(b * 255)
    
    def draw_display(self):
        """Draw the visual representation with zoom-dependent detail"""
        self.canvas.delete("all")
        
        viewport_range = self.viewport_end - self.viewport_start
        zoom_level = float(self.range_size_dec / viewport_range)
        values_per_pixel = viewport_range / Decimal(self.canvas_width)
        
        # Determine drawing resolution based on zoom
        if values_per_pixel > 100000:
            # Very zoomed out - draw in larger chunks
            step = 4
        elif values_per_pixel > 1000:
            # Moderately zoomed out
            step = 2
        else:
            # Zoomed in - draw every pixel
            step = 1
        
        # Draw the main visualization
        for x in range(0, self.canvas_width, step):
            # Calculate value at this position
            position = Decimal(x) / Decimal(self.canvas_width)
            value = self.viewport_start + position * viewport_range
            value_int = int(value)
            
            # Get color based on value and zoom level
            color = self.get_color_for_value(value_int, zoom_level)
            
            # Draw vertical line or rectangle
            if step > 1:
                self.canvas.create_rectangle(x, 0, x + step, self.canvas_height,
                                           fill=color, outline='')
            else:
                self.canvas.create_line(x, 0, x, self.canvas_height,
                                      fill=color, width=1)
        
        # Draw grid lines at high zoom levels
        if zoom_level > 100000:
            self.draw_grid_lines()
        
        # Draw scale markers
        self.draw_scale_markers()
        
        # Draw center line
        center_x = self.canvas_width // 2
        self.canvas.create_line(center_x, 0, center_x, self.canvas_height,
                              fill='white', width=2, dash=(5, 5))
    
    def draw_grid_lines(self):
        """Draw grid lines for better orientation at high zoom"""
        viewport_range = self.viewport_end - self.viewport_start
        
        # Calculate appropriate grid spacing
        grid_spacing = 1
        while grid_spacing * 20 < float(viewport_range):
            grid_spacing *= 16  # Hex-based spacing
        
        # Find first grid line
        start_grid = int(self.viewport_start / grid_spacing) * grid_spacing
        
        # Draw vertical grid lines
        for i in range(50):  # Limit iterations
            grid_value = start_grid + i * grid_spacing
            if grid_value > self.viewport_end:
                break
                
            x = int((Decimal(grid_value) - self.viewport_start) / 
                   (self.viewport_end - self.viewport_start) * self.canvas_width)
            
            if 0 <= x <= self.canvas_width:
                self.canvas.create_line(x, 0, x, self.canvas_height,
                                      fill='gray30', width=1)
    
    def draw_scale_markers(self):
        """Draw enhanced scale markers with better visibility"""
        num_markers = 10
        viewport_range = self.viewport_end - self.viewport_start
        zoom_level = float(self.range_size_dec / viewport_range)
        
        # Draw background for scale
        self.canvas.create_rectangle(0, self.canvas_height - 40, self.canvas_width, self.canvas_height,
                                   fill='gray20', outline='')
        
        for i in range(num_markers + 1):
            x = int(i * self.canvas_width / num_markers)
            
            # Tick marks - longer for major marks
            tick_height = 15 if i % 2 == 0 else 10
            self.canvas.create_line(x, self.canvas_height - tick_height, x, self.canvas_height,
                                  fill='white', width=2 if i % 2 == 0 else 1)
            
            # Hex value at this position
            position_dec = Decimal(i) / Decimal(num_markers)
            value_dec = self.viewport_start + position_dec * viewport_range
            value = int(value_dec)
            
            # Format hex string based on zoom level
            hex_str = f"{value:x}"
            
            # Show more detail when zoomed in
            if zoom_level > 1000:
                # Show full hex value
                display_str = f"0x{hex_str}"
            elif len(hex_str) > 8:
                # Truncate for readability
                display_str = f"{hex_str[:6]}..."
            else:
                display_str = hex_str
            
            # Only show labels for major marks to avoid crowding
            if i % 2 == 0 or zoom_level > 100:
                self.canvas.create_text(x, self.canvas_height - tick_height - 5,
                                      text=display_str, fill='white',
                                      anchor='s', font=('Courier', 8))
    
    def get_value_at_position(self, x):
        """Calculate the exact hex value at a given canvas position using high precision"""
        # Use Decimal for precise calculation
        position_dec = Decimal(x) / Decimal(self.canvas_width)
        viewport_size = self.viewport_end - self.viewport_start
        
        # Calculate exact value
        value_dec = self.viewport_start + position_dec * viewport_size
        
        # Round to nearest integer
        value = int(value_dec.quantize(Decimal('1')))
        
        # Ensure within bounds
        value = max(self.range_start, min(self.range_end, value))
        
        return value
    
    def process_hex_value(self, value):
        """Process a hex value through all transformations"""
        size = 72
        hexSize = size // 4
        bin2 = bin(value)[2:].zfill(size)[:size]
        for inv in range(2):
            for z in range(2):
                for y in range(size):
                    pp = int(bin2, 2)
                    hex2 = hex(pp)[2:].zfill(hexSize)
                    for x in range(16):
                        p = int('1' + hex2, 16)
                        address = ice.privatekey_to_address(0, True, p)

                        if y == 0 and z == 0 and inv == 0 and x == 0:
                            print(bin2 + ' - ' + hex(p)[2:] + ' -> ' + address)
                            
                        if address == target: 
                            print(hex(p)[2:] + ' -> ' + address)
                            print('found')
                            with open('found.txt', 'a') as file:
                                file.write(hex(p)[2:] + ' -> ' + address + "\n")
                            return True
                        hex2 = rotate_hex(hex2)
                    bin2 = shift_left(bin2, 1)
                bin2 = bin2[::-1]
            bin2 = inverse(bin2)
        return False
    
    def set_direction(self, direction):
        """Set scroll direction"""
        self.auto_scroll_direction = direction
        if direction > 0:
            self.direction_button.config(text="Direction: →")
        else:
            self.direction_button.config(text="Direction: ←")
    
    def increase_speed(self):
        """Increase scroll speed"""
        new_speed = min(10.0, self.auto_scroll_speed + 0.5)
        self.speed_var.set(new_speed)
        self.update_speed(new_speed)
    
    def decrease_speed(self):
        """Decrease scroll speed"""
        new_speed = max(0.1, self.auto_scroll_speed - 0.5)
        self.speed_var.set(new_speed)
        self.update_speed(new_speed)
    
    def on_mouse_move(self, event):
        """Handle mouse movement"""
        # Stop auto-scroll when mouse moves
        if self.auto_scroll_enabled:
            self.toggle_auto_scroll()
        
        self.last_mouse_x = event.x
        
        value = self.get_value_at_position(event.x)
        
        # Process hex value
        self.process_hex_value(value)
            
        # Update labels with enhanced information
        self.position_label.config(text=f"Position: ({event.x}, {event.y})")
        self.hex_label.config(text=f"Hex: 0x{value:x}")
        self.decimal_label.config(text=f"Decimal: {value:,}")
        
        # Draw enhanced crosshair
        self.canvas.delete("crosshair")
        
        # Vertical line
        self.canvas.create_line(event.x, 0, event.x, self.canvas_height - 40,
                              fill='yellow', width=1, tags="crosshair")
        # Horizontal line
        self.canvas.create_line(0, event.y, self.canvas_width, event.y,
                              fill='yellow', width=1, tags="crosshair", dash=(3, 3))
        
        # Highlight current value on scale
        self.canvas.create_rectangle(event.x - 2, self.canvas_height - 40,
                                   event.x + 2, self.canvas_height,
                                   fill='yellow', tags="crosshair")
    
    def on_click(self, event):
        """Handle mouse click - start dragging"""
        self.drag_start_x = event.x
        self.drag_start_viewport = (self.viewport_start, self.viewport_end)
        
    def on_drag(self, event):
        """Handle mouse drag - pan the view"""
        if self.drag_start_x is None:
            return
            
        # Calculate drag distance as fraction of canvas
        drag_fraction = Decimal(self.drag_start_x - event.x) / Decimal(self.canvas_width)
        
        # Calculate offset
        viewport_size = self.drag_start_viewport[1] - self.drag_start_viewport[0]
        offset = drag_fraction * viewport_size
        
        # Update viewport
        self.viewport_start = self.drag_start_viewport[0] + offset
        self.viewport_end = self.drag_start_viewport[1] + offset
        
        # Clamp to valid range
        if self.viewport_start < self.range_start_dec:
            self.viewport_end = self.viewport_end + (self.range_start_dec - self.viewport_start)
            self.viewport_start = self.range_start_dec
        elif self.viewport_end > self.range_end_dec:
            self.viewport_start = self.viewport_start - (self.viewport_end - self.range_end_dec)
            self.viewport_end = self.range_end_dec
            
        # Redraw
        self.draw_display()
        self.update_zoom_info()
        
        # Process only the value at the center of the screen for better performance
        center_x = self.canvas_width // 2
        center_value = self.get_value_at_position(center_x)
        self.process_hex_value(center_value)
        
        # Update labels for current mouse position
        current_value = self.get_value_at_position(event.x)
        self.position_label.config(text=f"Position: ({event.x}, {event.y})")
        self.hex_label.config(text=f"Hex: 0x{current_value:x}")
        self.decimal_label.config(text=f"Decimal: {current_value:,}")
        
        # Draw crosshair
        self.canvas.delete("crosshair")
        self.canvas.create_line(event.x, 0, event.x, self.canvas_height - 40,
                              fill='yellow', width=1, tags="crosshair")
        self.canvas.create_line(0, event.y, self.canvas_width, event.y,
                              fill='yellow', width=1, tags="crosshair", dash=(3, 3))
        self.canvas.create_rectangle(event.x - 2, self.canvas_height - 40,
                                   event.x + 2, self.canvas_height,
                                   fill='yellow', tags="crosshair")
    
    def on_mouse_release(self, event):
        """Handle mouse button release - stop dragging"""
        self.drag_start_x = None
        self.drag_start_viewport = None
        # Trigger a mouse move event to update the hex generation at the new position
        self.on_mouse_move(event)
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for Windows/MacOS"""
        # Get value under mouse before zoom
        value_under_mouse = Decimal(self.get_value_at_position(event.x))
        
        # Calculate zoom factor - more gradual zooming
        if event.delta > 0:  # Zoom in
            zoom_factor = Decimal('0.9')
        else:  # Zoom out
            zoom_factor = Decimal('1.11')
            
        self.apply_zoom(zoom_factor, event.x, value_under_mouse)
    
    def on_mouse_wheel_linux_up(self, event):
        """Handle mouse wheel up for Linux"""
        value_under_mouse = Decimal(self.get_value_at_position(event.x))
        self.apply_zoom(Decimal('0.9'), event.x, value_under_mouse)
    
    def on_mouse_wheel_linux_down(self, event):
        """Handle mouse wheel down for Linux"""
        value_under_mouse = Decimal(self.get_value_at_position(event.x))
        self.apply_zoom(Decimal('1.11'), event.x, value_under_mouse)
        
    def apply_zoom(self, zoom_factor, mouse_x, value_under_mouse):
        """Apply zoom transformation"""
        # Calculate mouse position as fraction
        mouse_fraction = Decimal(mouse_x) / Decimal(self.canvas_width)
        
        # Current viewport size
        old_size = self.viewport_end - self.viewport_start
        
        # New viewport size
        new_size = old_size * zoom_factor
        
        # Minimum size (at least 1 value)
        if new_size < 1:
            new_size = Decimal('1')
        
        # Maximum size (entire range)
        if new_size > self.range_size_dec:
            new_size = self.range_size_dec
            
        # Calculate new viewport to keep value under mouse at same position
        new_start = value_under_mouse - mouse_fraction * new_size
        new_end = new_start + new_size
        
        # Adjust if outside bounds
        if new_start < self.range_start_dec:
            new_end = new_end + (self.range_start_dec - new_start)
            new_start = self.range_start_dec
        elif new_end > self.range_end_dec:
            new_start = new_start - (new_end - self.range_end_dec)
            new_end = self.range_end_dec
            
        self.viewport_start = new_start
        self.viewport_end = new_end
        
        # Redraw
        self.draw_display()
        self.update_zoom_info()
        
    def update_zoom_info(self):
        """Update zoom information label with enhanced details"""
        viewport_size = self.viewport_end - self.viewport_start
        zoom_level = self.range_size_dec / viewport_size
        
        # Calculate values per pixel
        values_per_pixel = viewport_size / Decimal(self.canvas_width)
        
        start_int = int(self.viewport_start)
        end_int = int(self.viewport_end)
        
        # Format zoom level
        if zoom_level > 1000000:
            zoom_str = f"{float(zoom_level):.2e}x"
        else:
            zoom_str = f"{float(zoom_level):.2f}x"
        
        # Create info text
        info_text = f"Zoom: {zoom_str} | Range: 0x{start_int:x} - 0x{end_int:x}"
        
        # Add viewport size info
        if viewport_size < 1000:
            info_text += f" | Size: {int(viewport_size)} values"
        else:
            info_text += f" | Size: {float(viewport_size):.2e} values"
        
        self.zoom_info_label.config(text=info_text)
        
        # Update window title
        if values_per_pixel > 1:
            vpp_str = f"{float(values_per_pixel):.2e}" if values_per_pixel > 1000 else f"{float(values_per_pixel):.2f}"
            self.root.title(f"Hex Range Explorer - {vpp_str} values/pixel")
        else:
            pixels_per_value = 1 / float(values_per_pixel)
            self.root.title(f"Hex Range Explorer - {pixels_per_value:.1f} pixels/value")

def main():
    root = tk.Tk()
    app = HexRangeExplorer(root)
    
    # Ensure the window gets focus for mouse wheel events
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    
    root.mainloop()

if __name__ == "__main__":
    main()