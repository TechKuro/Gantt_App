import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib as mpl
from matplotlib.patches import Patch

# Increase default font size for better readability
mpl.rcParams['font.size'] = 14
mpl.rcParams['axes.titlesize'] = 18
mpl.rcParams['xtick.labelsize'] = 12
mpl.rcParams['ytick.labelsize'] = 12

# Define the project tasks with specific start and end dates
tasks = [
    {
        "name": "QuickBase - Single Sign On",
        "start": datetime(2025, 6, 23),
        "end": datetime(2025, 7, 4),
    },
    {
        "name": "HubSpot - Single Sign On",
        "start": datetime(2025, 6, 30),
        "end": datetime(2025, 7, 4),
    },
    {
        "name": "BambooHR - Single Sign On",
        "start": datetime(2025, 7, 7),
        "end": datetime(2025, 7, 11),
    },
    {
        "name": "Vestberry - Single Sign On",
        "start": datetime(2025, 7, 14),
        "end": datetime(2025, 7, 18),
    }
]

# --- Gantt Chart Logic ---

# 1. Find the project's date range
min_date = min(task['start'] for task in tasks)
max_date = max(task['end'] for task in tasks)

# 2. Generate a list of working days (Mon-Fri)
work_days = []
current_date = min_date
while current_date <= max_date:
    if current_date.weekday() < 5:  # Monday is 0, Sunday is 6
        work_days.append(current_date)
    current_date += timedelta(days=1)

# Add a few extra working days to the end for padding
padding_days_to_add = 3
days_added = 0
while days_added < padding_days_to_add:
    if current_date.weekday() < 5:
        work_days.append(current_date)
        days_added += 1
    current_date += timedelta(days=1)

# 3. Create a mapping from date to index for quick lookups
date_to_index = {date: i for i, date in enumerate(work_days)}


# Create figure and axes
fig, ax = plt.subplots(figsize=(18, 4))

# Plot each task based on working day indices
for i, task in enumerate(tasks):
    # Find all working days within the task's duration
    task_work_days = [d for d in work_days if task["start"] <= d <= task["end"]]
    
    if not task_work_days:
        continue  # Skip tasks that fall entirely on weekends

    start_index = date_to_index[task_work_days[0]]
    
    # Check for a specific duration override, otherwise calculate from dates
    if "duration" in task:
        duration_in_days = task["duration"]
    else:
        duration_in_days = len(task_work_days)
    
    ax.barh(y=i, width=duration_in_days, left=start_index, height=0.3, 
            color='#4f81bd', align='center', edgecolor='black', alpha=0.8)

# Configure y-axis
ax.set_yticks(range(len(tasks)))
ax.set_yticklabels([task["name"] for task in tasks])
ax.invert_yaxis()  # To display tasks from top to bottom

# Configure x-axis to show work days, not continuous time
ax.set_xticks(range(len(work_days)))
ax.set_xticklabels([d.strftime('%d-%b') for d in work_days])
plt.xticks(rotation=90, ha="center")
ax.set_xlim(-0.5, len(work_days) - 0.5)


# Add grid lines for better readability
ax.grid(axis='x', linestyle='--', alpha=0.6)

# Add titles and labels
ax.set_title('SSO Project Timeline')
ax.set_xlabel('Date')
ax.set_ylabel('Tasks')

# Improve layout and display the chart
plt.tight_layout()
plt.show()
