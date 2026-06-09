# Probability Calculator

This Python script calculates the number of runs required and the total time needed to achieve a target success probability based on a given drop chance and mission time. It allows you to input your target success chance, drop chance, and mission time (in hours, minutes, and seconds) to estimate how many runs and how much time it will take to achieve your desired success rate.

Now includes a modern, responsive Web GUI featuring a built-in stopwatch/run timer and interactive progression probability charts!

## Interactive Web GUI
To use the visual web version of the calculator, simply double-click or open [index.html](file:///C:/Users/Devy/Desktop/GitStuff/CodingChronicles/Probability%20Calculator/index.html) directly in any web browser. 

The Web GUI includes:
- **Interactive sliders** for setting success confidence and drop rate.
- **Integrated Run Stopwatch** to track your actual mission times and capture them with a single click.
- **Dynamic Progression Curve** showing how your success probability scales with each run.

## CLI & Script Features
- Calculates the number of runs required to achieve a target success chance.
- Computes the total time needed based on mission time and number of runs.
- Validates input values and provides error messages for invalid inputs.
- Provides results in a user-friendly format with color-coded output using `colorama`.





## If you want to use the python file
Follow the steps below

### Installing Dependencies

To install the required dependencies, run:

```bash
pip install colorama
```

## Requirements
- Python 3.x
- `colorama` library for colored terminal output