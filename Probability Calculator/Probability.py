import math, os
import keyboard as kb
from colorama import Fore, Back, Style






def calculate_runs(success_chance, drop_chance, mission_time):
    """
    Calculate the number of runs and time needed to achieve the desired success chance.
    
    Parameters:
    - success_chance (float): The target success probability (e.g., 0.99 for 99%).
    - drop_chance (float): The drop chance for each run (e.g., 0.05 for 5%).
    - mission_time (tuple): Time for each mission in (hours, minutes, seconds).
    
    Returns:
    - runs (int): The number of runs needed to achieve the target success chance.
    - total_time (tuple): The total time in (hours, minutes, seconds).
    """
    # Convert mission time to minutes
    mission_time_minutes = mission_time[0] * 60 + mission_time[1] + mission_time[2] / 60
    
    # Solve for number of runs
    runs = math.ceil(math.log(1 - success_chance) / math.log(1 - drop_chance))
    total_time_minutes = runs * mission_time_minutes
    total_time_hours = total_time_minutes // 60
    total_time_minutes = total_time_minutes % 60
    total_time_seconds = int((total_time_minutes % 1) * 60)
    total_time = (total_time_hours, int(total_time_minutes), total_time_seconds)
    return runs, total_time



def get_number_input(prompt, default, min_value=0):
    """Gets user input, ensuring it's a valid number within a valid range."""
    while True:
        try:
            value = input(prompt)
            value = float(value) if value else default
            if value < min_value:
                print(Fore.RED + f"Invalid input! Must be at least {min_value}." + Style.RESET_ALL)
                continue
            return value
        except ValueError:
            print(Fore.RED + "Invalid input! Please enter a number." + Style.RESET_ALL)




def main():
    print("""How to use:
1. Enter the success chance in percentage (e.g., 90).
2. Enter the drop chance in percentage (e.g., 5).
3. Enter the mission time in hours, minutes, and seconds (e.g., 0 1 0).

tip: Just press enter for default values (90, 5, 0 0 0)

Success chance is the probability you want to achieve.
For example, if you want to have at least a 90% chance of getting the drop, enter 90.
""")
    success_chance = get_number_input("Success chance: ", 90, 10) / 100
    success_chance = min(success_chance, 0.9999) # Prevents 100% success chance
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("Drop chance is the probability of dropping the item. \nFor example, if you have a 5% chance of dropping the item, enter 5.\n\n")
    drop_chance = get_number_input("Drop chance: ", 5, 0.0001) / 100  # Prevents 0% drop chance
    drop_chance = min(drop_chance, 0.9999)  # Prevents 100% drop chance
    os.system('cls' if os.name == 'nt' else 'clear')
    
    hours = int(get_number_input("Hours: ", 0, 0))
    minutes = int(get_number_input("Minutes: ", 0, 0))
    seconds = int(get_number_input("Seconds: ", 0, 0))
    mission_time = (hours, minutes, seconds)
    
    os.system('cls' if os.name == 'nt' else 'clear')
    
    runs, total_time = calculate_runs(
        success_chance, 
        drop_chance, 
        mission_time
    )
    
    print(Fore.GREEN + f"Number of runs needed: {runs:,}" + Style.RESET_ALL)
    print(Fore.CYAN + f"Total time needed: {int(total_time[0]):02d}:{int(total_time[1]):02d}:{int(total_time[2]):02d}" + Style.RESET_ALL)
    print("\n" * 5)



if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    main()
