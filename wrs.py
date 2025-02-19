import sys
import json
import pandas as pd
from datetime import datetime

# ✅ Define priority groups and their sub-groups
PRIORITY_GROUPS = {
    "A": ["A1", "A2"],
    "B": ["B1", "B2"],
    "C": ["C1", "C2"]
}

# ✅ Canal to priority sub-group mapping
CANAL_PRIORITY_MAP = {
    "A1": ["Chamman Disty", "Nal Disty", "Tarinda Disty", "Channa Minor"],
    "A2": ["Upper Wah Faquiran Disty", "Lower Wah Faquiran Disty", "Kacha Disty"],
    "B1": ["Azim Disty", "Pattan Munara Minor", "Kandera Disty", "Nal Disty"],
    "B2": ["Adam Sohaba Disty", "Talla Disty", "Chamman Disty", "Sianwar Minor"],
    "C1": ["Naushera Link Disty", "Naushera Minor", "Bagh Minor", "Malu Minor"],
    "C2": ["Manthar Disty", "Lakhi Minor", "Sultan Disty"]
}

def find_priority_group(canal_name):
    """
    Find the priority group and sub-group of a given canal.
    Returns: (main_group, sub_group) or (None, None) if not found.
    """
    for sub_group, canals in CANAL_PRIORITY_MAP.items():
        if canal_name in canals:
            for main_group, sub_groups in PRIORITY_GROUPS.items():
                if sub_group in sub_groups:
                    return main_group, sub_group
    return None, None

def load_csv_data(hierarchy_path, rotation_plan_path):
    """
    Loads the canal hierarchy and rotation plan CSV files.
    Ensures correct column formatting.
    """
    df_hierarchy = pd.read_csv(hierarchy_path)
    df_rotation = pd.read_csv(rotation_plan_path)

    # ✅ Strip spaces from column names
    df_rotation.columns = df_rotation.columns.str.strip()

    # ✅ Convert date columns to datetime
    df_rotation["Start Date"] = pd.to_datetime(
        df_rotation["Start Date"].astype(str).str.strip(), 
        errors="coerce", 
        dayfirst=True
    )
    df_rotation["End Date"] = pd.to_datetime(
        df_rotation["End Date"].astype(str).str.strip(), 
        errors="coerce", 
        dayfirst=True
    )

    return df_hierarchy, df_rotation

def find_main_disty(canal_name, df):
    """
    Given a canal name, trace its hierarchy up to the main distributary (Disty).
    Returns the parent distributary or None.
    """
    parent_map = dict(zip(df["CHANNEL_NA"].str.strip(), df["PARENT_CHA"].str.strip()))
    channel_type_map = dict(zip(df["CHANNEL_NA"].str.strip(), df["CHANNEL_TY"].str.strip()))

    current = canal_name.strip()
    while current in parent_map:
        parent = parent_map[current]
        if parent in channel_type_map and channel_type_map[parent] == "D":
            return parent  # Found the distributary
        if parent == current or parent not in parent_map:
            return None  # No valid distributary found
        current = parent

    return None  # If no distributary is found

def get_current_week_water_availability(main_group, sub_group, df_rotation):
    """
    Fetches water availability details for the current date or current week.
    Returns availability details or None if not found.
    """
    today = datetime.today().date()

    for _, row in df_rotation.iterrows():
        if sub_group in row and main_group in row:
            sub_priority = pd.to_numeric(row[sub_group], errors="coerce")
            group_priority = pd.to_numeric(row[main_group], errors="coerce")

            sub_priority = sub_priority if pd.notna(sub_priority) else 999
            group_priority = group_priority if pd.notna(group_priority) else 999
            
            start_date = row["Start Date"].date() if pd.notna(row["Start Date"]) else None
            end_date = row["End Date"].date() if pd.notna(row["End Date"]) else None

            # ✅ Check if today's date is within the range
            if start_date and end_date and start_date <= today <= end_date:
                return {
                    "Start Date": start_date.strftime("%d-%m-%Y"),
                    "End Date": end_date.strftime("%d-%m-%Y"),
                    "Group Priority": group_priority,
                    "Sub-Group Priority": sub_priority
                }
    return None

if __name__ == "__main__":
    try:
        # ✅ Read input arguments
        hierarchy_path = sys.argv[1]
        rotation_plan_path = sys.argv[2]
        user_canal = sys.argv[3].strip()

        # ✅ Load CSV data
        df_hierarchy, df_rotation = load_csv_data(hierarchy_path, rotation_plan_path)

        # ✅ Step 1: Check if canal is directly in the rotational plan
        main_group, sub_group = find_priority_group(user_canal)

        if main_group and sub_group:
            # ✅ Step 2: Retrieve current week availability
            availability = get_current_week_water_availability(main_group, sub_group, df_rotation)

            if availability:
                result = {
                    "canal": user_canal,
                    "priority_group": main_group,
                    "sub_group": sub_group,
                    "availability": availability
                }
            else:
                result = {
                    "canal": user_canal,
                    "message": "Canal is in the plan but no availability data for this week."
                }

        else:
            # ✅ Step 3: Find parent distributary if canal is not directly in the plan
            main_disty = find_main_disty(user_canal, df_hierarchy)

            if main_disty:
                main_group, sub_group = find_priority_group(main_disty)

                if main_group and sub_group:
                    availability = get_current_week_water_availability(main_group, sub_group, df_rotation)

                    if availability:
                        result = {
                            "canal": user_canal,
                            "parent_canal": main_disty,
                            "priority_group": main_group,
                            "sub_group": sub_group,
                            "availability": availability,
                            "message": "Canal is not directly in the plan, but its parent is."
                        }
                    else:
                        result = {
                            "canal": user_canal,
                            "parent_canal": main_disty,
                            "message": "No availability data found for the parent distributary in the current week."
                        }
                else:
                    result = {
                        "canal": user_canal,
                        "parent_canal": main_disty,
                        "message": "Canal and its parent are not in the rotational plan."
                    }
            else:
                result = {
                    "canal": user_canal,
                    "message": "No Canal found in the Rabi Season."
                }

        # ✅ Print JSON result
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
