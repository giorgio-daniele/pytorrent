def print_rgb(text, r, g, b):
    # Create the ANSI escape code for RGB color
    rgb_code  = f"\033[38;2;{r};{g};{b}m"
    # Reset the color back to default
    reset_code = "\033[39m"
    # Print the text with the RGB color
    print(f"{rgb_code}{text}{reset_code}")

def print_red(text):
    print_rgb(text, 255, 0, 0)  # Red color in RGB

def print_green(text):
    print_rgb(text, 0, 255, 0)  # Green color in RGB

def print_blue(text):
    print_rgb(text, 0, 0, 80)  # Blue color in RGB
    
def print_yellow(text):
    print_rgb(text, 255, 255, 0)  # Yellow color in RGB