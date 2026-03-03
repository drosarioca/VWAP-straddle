
import pandas as pd
import os

# Define Columns
columns = [
    "Name_Tag", "Strategy_Mode", "Years", 
    "Spot_Check_Hour", "Spot_Check_Min",
    "Enter_Hour", "Enter_Min", 
    "Exit_Hour", "Exit_Min",
    "Entry_Window_Mins", 
    "SL_Min", "SL_Max", 
    "Trail_Trigger", "Trail_Step", 
    "Rolling_Step", "Portfolio_SL"
]

# Create Dummy Data
data = [
    {
        "Name_Tag": "Variant_A_Base",
        "Strategy_Mode": "NON_ROLLING",
        "Years": "2024, 2025",
        "Spot_Check_Hour": 9, "Spot_Check_Min": 34,
        "Enter_Hour": 9, "Enter_Min": 34,
        "Exit_Hour": 15, "Exit_Min": 20,
        "Entry_Window_Mins": 30,
        "SL_Min": 10, "SL_Max": 20,
        "Trail_Trigger": 20, "Trail_Step": 10,
        "Rolling_Step": 80, "Portfolio_SL": 70
    },
    {
        "Name_Tag": "Variant_B_TightSL",
        "Strategy_Mode": "ROLLING_VWAP",
        "Years": "2024",
        "Spot_Check_Hour": 9, "Spot_Check_Min": 30,
        "Enter_Hour": 9, "Enter_Min": 30,
        "Exit_Hour": 15, "Exit_Min": 15,
        "Entry_Window_Mins": 15,
        "SL_Min": 5, "SL_Max": 15,
        "Trail_Trigger": 15, "Trail_Step": 5,
        "Rolling_Step": 100, "Portfolio_SL": 50
    }
]

df = pd.DataFrame(data, columns=columns)

# Save
output_path = "crosswalk_input_v2.xlsx"
df.to_excel(output_path, index=False)
print(f"Created {output_path}")
