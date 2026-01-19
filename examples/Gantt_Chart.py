import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import matplotlib as mpl

# Increase default font size for better readability
mpl.rcParams['font.size'] = 14
mpl.rcParams['axes.titlesize'] = 18
mpl.rcParams['xtick.labelsize'] = 12
mpl.rcParams['ytick.labelsize'] = 12

# Define the project phases with specific start and end dates
tasks = [
    {
        "name": "Discovery",
        "start": datetime(2025, 6, 23),
        "end": datetime(2025, 7, 18)
    },
    {
        "name": "Plan",
        "start": datetime(2025, 7, 21),
        "end": datetime(2025, 7, 25)
    },
    {
        "name": "Design",
        "start": datetime(2025, 7, 28),
        "end": datetime(2025, 8, 8)
    },
    {
        "name": "Build",
        "start": datetime(2025, 8, 11),
        "end": datetime(2025, 8, 28)
    },
    {
        "name": "Test",
        "start": datetime(2025, 8, 29),
        "end": datetime(2025, 9, 11)
    },
    {
        "name": "Deliver",
        "start": datetime(2025, 9, 12),
        "end": datetime(2025, 9, 18)
    },
    {
        "name": "Close",
        "start": datetime(2025, 9, 19),
        "end": datetime(2025, 9, 19)
    }
]

# Define a color palette for the phases
colors = [
    '#4f81bd', '#c0504d', '#9bbb59', '#8064a2', 
    '#4bacc6', '#f79646', '#db843d'
]

# Create figure and axes
fig, ax = plt.subplots(figsize=(18, 8))

# Plot each phase
for i, task in enumerate(tasks):
    start_date = task["start"]
    # The end date for plotting should be one day after the actual end date
    # to represent the full duration on the chart
    end_date = task["end"] + timedelta(days=1)
    
    start_num = mdates.date2num(start_date)
    end_num = mdates.date2num(end_date)
    duration = end_num - start_num
    
    ax.barh(y=i, width=duration, left=start_num, height=0.6, 
            color=colors[i % len(colors)], align='center', edgecolor='black', alpha=0.8)

# Configure y-axis
ax.set_yticks(range(len(tasks)))
ax.set_yticklabels([task["name"] for task in tasks])
ax.invert_yaxis()  # To display tasks from top to bottom

# Configure x-axis for dates
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b-%Y'))
plt.xticks(rotation=45, ha="right")

# Set x-axis limits to cover the project timeline plus some padding
project_start_date = datetime(2025, 6, 20)
project_end_date = datetime(2025, 9, 22)
ax.set_xlim(project_start_date, project_end_date)

# Add grid lines for better readability
ax.grid(axis='x', linestyle='--', alpha=0.6)

# Shade weekends
day = project_start_date
while day <= project_end_date:
    if day.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
        ax.axvspan(day, day + timedelta(days=1), facecolor='gray', alpha=0.2)
    day += timedelta(days=1)

# Add titles and labels
ax.set_title('MSP Onboarding Project Gantt Chart')
ax.set_xlabel('Date')
ax.set_ylabel('Project Phase')

# Improve layout and display the chart
plt.tight_layout()
plt.show()
