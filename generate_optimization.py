
import pandas as pd
import itertools
import datetime

# Define Ranges based on User Input (Iter 3)

# 1. Time Ranges (9:25 to 09:45)
# "Variable 09:25:00 to 09:45:00" - Every 3 mins
time_steps = [
    (9, 25), (9, 28), (9, 31), (9, 34), (9, 37), (9, 40), (9, 43)
]

# 2. Entry Window (20 to 40)
# "20 to 40 mins each 10 mins" -> 20, 30, 40
window_steps = [20, 30, 40]

# 3. Rolling Step (40 to 100)
# "40 to 100 each 20 points" -> 40, 60, 80, 100
rolling_steps = [40, 60, 80, 100]

# 4. TC / Trail Trigger (10 to 25)
# "10 to 25 each 5 points" -> 10, 15, 20, 25
trail_triggers = [10, 15, 20, 25]

# 5. Trail / Trail Step (10 to 20)
# "10 to 20 each 5 points" -> 10, 15, 20
trail_steps = [10, 15, 20]

# 6. SL Ranges
# Min SL: 5 to 15 (5 pts increment) -> 5, 10, 15
# Max SL: 15 to 25 (5 pts increment) -> 15, 20, 25
sl_pairs = []
for min_sl in range(5, 16, 5): # 5, 10, 15
    for max_sl in range(15, 26, 5): # 15, 20, 25
        if min_sl <= max_sl:
            sl_pairs.append((min_sl, max_sl))

# Generate Full Combinations
combinations = []
id_counter = 1

for t_hour, t_min in time_steps:
    for win in window_steps:
        for roll in rolling_steps:
            for trigger in trail_triggers:
                for t_step in trail_steps:
                    for sl_min, sl_max in sl_pairs:
                        
                        variant = {
                            "Name_Tag": f"Var_{id_counter:04d}",
                            "Strategy_Mode": "NON_ROLLING",
                            "Years": "2021, 2022, 2023, 2024, 2025", 
                            "Spot_Check_Hour": t_hour, "Spot_Check_Min": t_min,
                            "Enter_Hour": t_hour, "Enter_Min": t_min,
                            "Exit_Hour": 15, "Exit_Min": 20,
                            "Entry_Window_Mins": win,
                            "Rolling_Step": roll,
                            "Trail_Trigger": trigger,
                            "Trail_Step": t_step,
                            "SL_Min": sl_min,
                            "SL_Max": sl_max,
                            "Portfolio_SL": 70
                        }
                        combinations.append(variant)
                        id_counter += 1

df = pd.DataFrame(combinations)
print(f"Generated {len(df)} variants (Full Set).")
df.to_excel("optimization_full.xlsx", index=False)

# --- SMART SAMPLE GENERATION ---
# Reduce steps to make it manageable (~400 variants)

# 1. Time: Start, Mid, End
time_steps_smart = [(9, 25), (9, 35), (9, 45)]

# 2. Window: Keep all (3)
window_steps_smart = [20, 30, 40]

# 3. Rolling: Start, Mid, End
rolling_steps_smart = [40, 70, 100]

# 4. Others: Endpoints only
trigger_smart = [10, 25]
trail_step_smart = [10, 20]

# SL Pairs: Endpoints combos
sl_pairs_smart = []
for min_sl in [5, 15]:
    for max_sl in [15, 25]:
        if min_sl <= max_sl:
            sl_pairs_smart.append((min_sl, max_sl))

combos_smart = []
tag_counter = 1

for t_hour, t_min in time_steps_smart:
    for win in window_steps_smart:
        for roll in rolling_steps_smart:
            for trigger in trigger_smart:
                for t_step in trail_step_smart:
                    for sl_min, sl_max in sl_pairs_smart:
                        
                        variant = {
                            "Name_Tag": f"Smart_{tag_counter:03d}",
                            "Strategy_Mode": "NON_ROLLING",
                            "Years": "2021, 2022, 2023, 2024, 2025", 
                            "Spot_Check_Hour": t_hour, "Spot_Check_Min": t_min,
                            "Enter_Hour": t_hour, "Enter_Min": t_min,
                            "Exit_Hour": 15, "Exit_Min": 20,
                            "Entry_Window_Mins": win,
                            "Rolling_Step": roll,
                            "Trail_Trigger": trigger,
                            "Trail_Step": t_step,
                            "SL_Min": sl_min,
                            "SL_Max": sl_max,
                            "Portfolio_SL": 70
                        }
                        combos_smart.append(variant)
                        tag_counter += 1

df_smart = pd.DataFrame(combos_smart)
print(f"Generated {len(df_smart)} variants (Smart Sample).")
df_smart.to_excel("optimization_smart.xlsx", index=False)
