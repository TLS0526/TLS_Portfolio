# ficheiro VisualizationHelper.py
class VisualizationHelper:
    """
    Helper class for terminal-based grid visualization with colors.

    Provides static helper methods to render a visualization of the simulation grid. 
    Smart bins, recycling centers and trucks are displayed using different colors and icons, allowing the user to monitor the positions and interactions in real time.
    """
    @staticmethod
    def draw_grid(truck_positions, bin_positions, rc_positions, grid_size):
        """
        Draw a colored grid in the terminal showing ALL agents
        
        Args:
            truck_positions (dict): Dictionary with truck names as keys and (x, y) tuples as values
            bin_positions (dict): Dictionary with bin names as keys and (x, y) tuples as values
            rc_positions (dict): Dictionary with RC names as keys and (x, y) tuples as values
            grid_size (int): Size of the grid (default 11x11)
        """
        # Uncomment to clear screen each time
        # VisualizationHelper.clear_screen()
        
        # ANSI color codes
        RESET = "\033[0m"
        RED = "\033[91m"
        GREEN = "\033[92m"
        BLUE = "\033[94m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        MAGENTA = "\033[95m"
        ORANGE = "\033[38;5;208m"
        PURPLE = "\033[38;5;135m"
        BOLD = "\033[1m"
        
        # Initialize empty grid
        grid = [['·' for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Place ALL Bins (different shades of red/orange)
        bin_colors = [RED, ORANGE, f"\033[38;5;196m", f"\033[38;5;202m"]  # Different reds
        if bin_positions:
            for idx, (name, pos) in enumerate(bin_positions.items()):
                if 0 <= pos[0] < grid_size and 0 <= pos[1] < grid_size:
                    color = bin_colors[idx % len(bin_colors)]
                    grid[pos[1]][pos[0]] = f"{color}{BOLD}🗑{RESET}"
        
        # Place ALL Recycling Centers (different shades of green)
        rc_colors = [GREEN, f"\033[38;5;46m", f"\033[38;5;34m", f"\033[38;5;40m"]
        if rc_positions:
            for idx, (name, pos) in enumerate(rc_positions.items()):
                if 0 <= pos[0] < grid_size and 0 <= pos[1] < grid_size:
                    color = rc_colors[idx % len(rc_colors)]
                    grid[pos[1]][pos[0]] = f"{color}{BOLD}♻{RESET}"
        
        # Place Trucks (different colors and symbols)
        truck_symbols = ['🚛', '🚚', '🚙', '🚐']
        truck_colors = [BLUE, YELLOW, CYAN, MAGENTA]
        
        if truck_positions:
            for idx, (name, pos) in enumerate(truck_positions.items()):
                if 0 <= pos[0] < grid_size and 0 <= pos[1] < grid_size:
                    color = truck_colors[idx % len(truck_colors)]
                    symbol = truck_symbols[idx % len(truck_symbols)]
                    grid[pos[1]][pos[0]] = f"{color}{BOLD}{symbol}{RESET}"
        
        # Draw top border
        print(f"\n{BOLD}╔" + "═" * (grid_size * 2 + 1) + "╗" + RESET)
        
        # Draw grid rows
        for row_idx, row in enumerate(grid):
            print(f"{BOLD}║{RESET} " + " ".join(row) + f" {BOLD}║{RESET} {row_idx}")
        
        # Draw bottom border
        print(f"{BOLD}╚" + "═" * (grid_size * 2 + 1) + "╝" + RESET)
        
        # Draw column numbers
        col_numbers = "  " + " ".join([str(i) for i in range(grid_size)])
        print(col_numbers)
        
        # Draw legend
        print(f"\n{BOLD}═══ Legend ═══{RESET}")
        print(f"  {RED}{BOLD}🗑{RESET}  = Smart Bins")
        print(f"  {GREEN}{BOLD}♻{RESET}  = Recycling Centers")
        print(f"  {BLUE}{BOLD}🚛{RESET}  = Trucks")
        print(f"  {BOLD}·{RESET}  = Empty space")
        
        print("═" * 40)
