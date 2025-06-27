from datetime import datetime, timedelta
import math

# --- Core Calculation Logic ---

def add_work_days(start_date, duration_days):
    end_date = start_date
    days_to_add = math.ceil(duration_days) - 1
    if duration_days > 0 and days_to_add < 0:
        days_to_add = 0
    temp_date = start_date
    while days_to_add > 0:
        temp_date += timedelta(days=1)
        if temp_date.weekday() < 5:
            days_to_add -= 1
    end_date = temp_date
    return end_date

def count_work_days(start_date, end_date):
    """Counts the number of work days (Mon-Fri) between two dates, inclusive."""
    if start_date > end_date:
        return 0
    
    work_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:
            work_days += 1
        current_date += timedelta(days=1)
    return work_days

def calculate_task_dates(tasks_list, project_start_date):
    # Clear all previously calculated dates to ensure a fresh calculation
    for task in tasks_list:
        if 'start' in task: del task['start']
        if 'end' in task: del task['end']
        for sub_task in task.get('sub_tasks', []):
            if 'start' in sub_task: del sub_task['start']
            if 'end' in sub_task: del sub_task['end']

    tasks_by_name = {task["name"]: task for task in tasks_list}
    calculated_tasks = set()

    for _ in range(len(tasks_list) * 2): # Increased loop for safety with sub-tasks
        made_progress = False
        for task in tasks_list:
            if task["name"] in calculated_tasks:
                continue

            # Determine the start date for the first sub-task
            start_date_for_task = None
            override_str = task.get("start_date_override")
            dependency_name = task.get("depends_on")

            if override_str:
                try:
                    start_date_for_task = datetime.strptime(override_str, "%d-%m-%Y")
                    # If the override date falls on a weekend, move it to the next Monday
                    while start_date_for_task.weekday() >= 5:
                        start_date_for_task += timedelta(days=1)
                except ValueError:
                    raise ValueError(f"Invalid date format for '{task['name']}'. Please use DD-MM-YYYY.")
            elif dependency_name:
                if dependency_name in calculated_tasks:
                    dependency = tasks_by_name[dependency_name]
                    next_day = dependency["end"] + timedelta(days=1)
                    while next_day.weekday() >= 5:
                        next_day += timedelta(days=1)
                    start_date_for_task = next_day
            else:
                # Base task (not pinned, no dependency)
                start_date_for_task = project_start_date

            # If we have a start date, we can calculate this task and its sub-tasks
            if start_date_for_task:
                last_sub_task_end = None
                
                # Check for a task-level end date override, which dictates the parent task's end.
                end_date_override_str = task.get("end_date_override")
                end_date_override = None
                if end_date_override_str:
                    try:
                        parsed_date = datetime.strptime(end_date_override_str, "%d-%m-%Y")
                        if parsed_date >= start_date_for_task:
                            end_date_override = parsed_date
                    except ValueError:
                        pass # Invalid format, ignore override

                # Holds the precise end moment of the last sub-task (can be fractional)
                cumulative_duration_days = 0 

                for i, sub_task in enumerate(task.get("sub_tasks", [])):
                    # The duration is always taken from the sub_task data itself,
                    # which may have been calculated by the Edit dialog.
                    current_duration = sub_task['duration']
                    
                    # Determine earliest possible start date based on predecessor, using
                    # a running total of fractional days to maintain precision.
                    if i == 0:
                        sub_task["start"] = start_date_for_task
                    else:
                        sub_task["start"] = add_work_days(start_date_for_task, cumulative_duration_days)
                    
                    sub_task["end"] = add_work_days(sub_task["start"], current_duration)
                    cumulative_duration_days += current_duration
                
                # Set the parent task's start and end
                if task.get("sub_tasks"):
                    task["start"] = task["sub_tasks"][0]["start"]
                    if end_date_override:
                        # If a valid override exists, use it for the parent task's visual container.
                        task["end"] = end_date_override
                    else:
                        # Otherwise, calculate the end based on the sum of stage durations.
                        total_duration = sum(st.get('duration', 0) for st in task.get('sub_tasks', []))
                        task["end"] = add_work_days(task["start"], total_duration)
                else: # Task with no sub-tasks
                    task["start"] = start_date_for_task
                    task["end"] = add_work_days(start_date_for_task, 0)
                
                calculated_tasks.add(task["name"])
                made_progress = True

        if len(calculated_tasks) == len(tasks_list):
            return tasks_list
        if not made_progress and len(calculated_tasks) < len(tasks_list):
            uncalculated = [t['name'] for t in tasks_list if t['name'] not in calculated_tasks]
            raise ValueError(f"Circular dependency or missing task. Uncalculated: {uncalculated}")
    
    return tasks_list 