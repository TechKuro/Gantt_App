import pandas as pd
from tkinter import messagebox
from dialogs import ColumnMappingDialog

def import_from_file(filepath, parent):
    """
    Imports tasks from a CSV or Excel file.
    """
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filepath.endswith('.xls') or filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            messagebox.showerror("Unsupported File Type", "Please select a CSV or Excel file.")
            return None
    except Exception as e:
        messagebox.showerror("Error Reading File", f"An error occurred while reading the file: {e}")
        return None

    dialog = ColumnMappingDialog(parent, "Map Columns", list(df.columns))
    if not dialog.mapping:
        return None # User cancelled

    # Basic validation
    if not dialog.mapping.get("Task Name"):
        messagebox.showerror("Mapping Error", "You must map a column to 'Task Name'.")
        return None
    
    tasks_data = []
    for index, row in df.iterrows():
        try:
            task_name_col = dialog.mapping["Task Name"]
            task_name = row[task_name_col]

            if pd.isna(task_name):
                continue # Skip rows where task name is empty
            
            # For now, we will treat each row as a new parent task with one sub-task/stage.
            # More complex structures can be handled later.

            new_task = {
                "name": str(task_name),
                "sub_tasks": []
            }

            if dialog.mapping.get("Start Date"):
                start_date_str = str(row[dialog.mapping["Start Date"]])
                if start_date_str and not pd.isna(start_date_str):
                    new_task["start_date_override"] = start_date_str

            if dialog.mapping.get("End Date"):
                end_date_str = str(row[dialog.mapping["End Date"]])
                if end_date_str and not pd.isna(end_date_str):
                    new_task["end_date_override"] = end_date_str

            if dialog.mapping.get("Dependencies"):
                 depends_on_str = str(row[dialog.mapping["Dependencies"]])
                 if depends_on_str and not pd.isna(depends_on_str):
                     new_task['depends_on'] = depends_on_str


            # Create a sub-task (stage) from the row
            stage_name = "Default Stage"
            if dialog.mapping.get("Stage") and not pd.isna(row[dialog.mapping["Stage"]]):
                stage_name = str(row[dialog.mapping["Stage"]])

            status = "Not Started"
            if dialog.mapping.get("Status") and not pd.isna(row[dialog.mapping["Status"]]):
                status = str(row[dialog.mapping["Status"]])

            # Since we don't have duration directly, we'll let the core logic calculate it
            # from start/end dates if available. We'll set a placeholder duration.
            new_sub_task = {
                "name": stage_name,
                "duration": 1, 
                "status": status
            }

            new_task["sub_tasks"].append(new_sub_task)
            tasks_data.append(new_task)

        except KeyError as e:
            messagebox.showerror("Mapping Error", f"The column '{e}' selected in the mapping does not exist in the file.")
            return None
        except Exception as e:
            messagebox.showerror("Import Error", f"An error occurred while processing row {index+2}: {e}")
            return None
            
    return tasks_data 