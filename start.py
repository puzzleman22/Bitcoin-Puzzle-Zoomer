import tkinter as tk
from tkinter import ttk
from decimal import Decimal, getcontext
import secp256k1 as ice
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
        
        # Precise viewport tracking using Decimal
        self.viewport_start = Decimal(self.range_start)
        self.viewport_end = Decimal(self.range_end)
        
        # Bind mouse events - fix platform-specific bindings
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        
        # Platform-specific mouse wheel bindings
        # Windows and MacOS
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        # Linux
        self.canvas.bind("<Button-4>", self.on_mouse_wheel_linux_up)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel_linux_down)
        
        # Focus canvas to receive events
        self.canvas.focus_set()
        
        # For dragging
        self.drag_start_x = None
        self.drag_start_viewport = None
        
        # Store last mouse position
        self.last_mouse_x = self.canvas_width // 2
        
        # Draw initial display
        self.draw_display()
        
    def draw_display(self):
        """Draw the visual representation"""
        self.canvas.delete("all")
        
        # Draw gradient
        for x in range(0, self.canvas_width, 2):
            position = x / self.canvas_width
            intensity = int(255 * position)
            color = f'#{intensity:02x}{(255-intensity):02x}{128:02x}'
            self.canvas.create_line(x, 0, x, self.canvas_height, 
                                  fill=color, width=2)
        
        # Draw center line
        center_x = self.canvas_width // 2
        self.canvas.create_line(center_x, 0, center_x, self.canvas_height,
                              fill='red', width=2)
        
        # Draw scale markers
        self.draw_scale_markers()
        
    def draw_scale_markers(self):
        """Draw scale markers on the canvas"""
        # Draw markers at regular intervals
        num_markers = 10
        for i in range(num_markers + 1):
            x = int(i * self.canvas_width / num_markers)
            
            # Draw tick
            self.canvas.create_line(x, self.canvas_height - 20, x, self.canvas_height,
                                  fill='white', width=1)
            
            # Calculate value at this position using Decimal
            position_dec = Decimal(i) / Decimal(num_markers)
            value_dec = self.viewport_start + position_dec * (self.viewport_end - self.viewport_start)
            value = int(value_dec)
            
            # Create abbreviated hex label
            hex_str = f"{value:x}"
            if len(hex_str) > 8:
                hex_str = hex_str[:6] + ".."
                
            self.canvas.create_text(x, self.canvas_height - 25, text=hex_str,
                                  fill='white', anchor='s', font=('Courier', 8))
    
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
    
    def on_mouse_move(self, event):
        """Handle mouse movement"""
        self.last_mouse_x = event.x
        
        value = self.get_value_at_position(event.x)
        
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
                            return
                        hex2 = rotate_hex(hex2)
                    bin2 = shift_left(bin2, 1)
                bin2 = bin2[::-1]
            bin2 = inverse(bin2)
        # Update labels
        self.position_label.config(text=f"Position: ({event.x}, {event.y})")
        self.hex_label.config(text=f"Hex: 0x{value:x}")
        self.decimal_label.config(text=f"Decimal: {value:,}")
        
        # Draw crosshair
        self.canvas.delete("crosshair")
        self.canvas.create_line(event.x, 0, event.x, self.canvas_height,
                              fill='yellow', width=1, tags="crosshair")
        self.canvas.create_line(0, event.y, self.canvas_width, event.y,
                              fill='yellow', width=1, tags="crosshair")
    
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
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for Windows/MacOS"""
        # Get value under mouse before zoom
        value_under_mouse = Decimal(self.get_value_at_position(event.x))
        
        # Calculate zoom factor
        if event.delta > 0:  # Zoom in
            zoom_factor = Decimal('0.8')
        else:  # Zoom out
            zoom_factor = Decimal('1.25')
            
        self.apply_zoom(zoom_factor, event.x, value_under_mouse)
    
    def on_mouse_wheel_linux_up(self, event):
        """Handle mouse wheel up for Linux"""
        value_under_mouse = Decimal(self.get_value_at_position(event.x))
        self.apply_zoom(Decimal('0.8'), event.x, value_under_mouse)
    
    def on_mouse_wheel_linux_down(self, event):
        """Handle mouse wheel down for Linux"""
        value_under_mouse = Decimal(self.get_value_at_position(event.x))
        self.apply_zoom(Decimal('1.25'), event.x, value_under_mouse)
        
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
        """Update zoom information label"""
        viewport_size = self.viewport_end - self.viewport_start
        zoom_level = self.range_size_dec / viewport_size
        
        # Calculate values per pixel
        values_per_pixel = viewport_size / Decimal(self.canvas_width)
        
        start_int = int(self.viewport_start)
        end_int = int(self.viewport_end)
        
        self.zoom_info_label.config(
            text=f"Zoom: {float(zoom_level):.2f}x | Visible: 0x{start_int:x} - 0x{end_int:x}"
        )
        
        # Update window title
        if values_per_pixel > 1:
            vpp_str = f"{float(values_per_pixel):.2e}" if values_per_pixel > 1000 else f"{float(values_per_pixel):.2f}"
            self.root.title(f"Hex Range Explorer - {vpp_str} values per pixel")
        else:
            self.root.title("Hex Range Explorer - Sub-pixel precision")

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