# Gantt Chart Planner - User Guide

A desktop application for creating, managing, and visualizing project schedules with Gantt charts.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Projects](#creating-projects)
3. [Managing Tasks](#managing-tasks)
4. [Working with Dependencies](#working-with-dependencies)
5. [Using the Gantt Chart](#using-the-gantt-chart)
6. [Stages and Status](#stages-and-status)
7. [Filtering and Sorting](#filtering-and-sorting)
8. [Saving and Exporting](#saving-and-exporting)
9. [Keyboard Shortcuts](#keyboard-shortcuts)
10. [Tips and Best Practices](#tips-and-best-practices)

---

## Getting Started

### Launching the Application

```bash
python main.py
```

### First Launch

When you first open the application, you'll see:
- **Left panel**: Project settings and task list
- **Right panel**: Gantt chart visualization
- **Status bar**: Task count and save status

### Quick Start

1. **Load Sample Project**: `File → Load Sample Project` to see a demo
2. **Or create your first task**: Type a task name in the "Quick add" box and press Enter

---

## Creating Projects

### New Blank Project

`File → New Blank Project`

Creates an empty project. You'll need to:
1. Set the project name
2. Set the project start date (DD-MM-YYYY format)
3. Add tasks

### Load Sample Project

`File → Load Sample Project`

Loads a pre-built demo project with 5 tasks showing:
- Dependencies between tasks
- Different completion statuses
- Typical project workflow

### Load from Template

`File → Load Template...`

Opens a `.gantt_template` file that contains task structures without specific dates. Great for repeatable project types.

### Open Existing Project

`File → Open Project...`

Opens a previously saved `.gantt` project file.

---

## Managing Tasks

### Adding Tasks

#### Quick Add (Recommended)
1. Click in the "Quick add" box at the top of the task list
2. Type the task name
3. Press **Enter**

The task is created with default stages (Preparation, Implementation, Training/Adoption) each with 1-day duration.

#### Add Task Button
Click **+ Add Task** to add a new task with default settings.

### Editing Tasks

#### Inline Editing (Fast)
Double-click any cell in the task list to edit it directly:

| Column | What You Can Edit |
|--------|------------------|
| **Task Name** | Rename the task (parent rows only) |
| **Days** | Change stage duration (sub-task rows only) |
| **Status** | Set stage status via dropdown (sub-task rows only) |
| **Depends On** | Set task dependency via dropdown (parent rows only) |
| **Start** | Override start date in DD-MM-YYYY format (parent rows only) |

Press **Enter** to confirm or **Escape** to cancel.

#### Full Edit Dialog
1. Select a task
2. Click **Edit** or press **Enter**
3. The edit dialog allows you to:
   - Change task name
   - Set dependencies
   - Override start/end dates
   - Modify all stage durations and statuses
   - Add or remove stages

### Removing Tasks

1. Select a task in the list
2. Click **Remove** or press **Delete**
3. Confirm the deletion

**Note**: Removing a task will clear any dependencies other tasks have on it.

### Reordering Tasks

1. Click and hold on a parent task row
2. Drag it to a new position
3. Release to drop

The Gantt chart will update to reflect the new order.

---

## Working with Dependencies

Dependencies define which tasks must complete before others can start.

### Setting a Dependency

#### Method 1: Inline Edit
1. Double-click the "Depends On" column for a task
2. Select the predecessor task from the dropdown
3. The task will automatically start after its predecessor ends

#### Method 2: Edit Dialog
1. Open the Edit Task dialog
2. Select a task from the "Depends On" dropdown

### Dependency Rules

- **Finish-to-Start (FS)**: A task starts the day after its predecessor finishes
- **Weekend Skipping**: If the predecessor ends on Friday, the dependent task starts Monday
- **Single Dependency**: Each task can depend on one other task
- **No Cycles**: The app prevents circular dependencies (A→B→A)

### Cycle Detection

If you try to create a circular dependency, you'll see an error:
```
Circular dependency detected:
  Task A → Task B → Task C → Task A
```

Remove one of the dependencies to fix the issue.

### Auto-Schedule Mode

Enable **Auto-Schedule** in Project Settings to automatically shift dependent tasks when you move a predecessor:

1. Check "Auto-Schedule" in Project Settings
2. Drag a task to a new date
3. All dependent tasks (direct and transitive) shift automatically

**Without Auto-Schedule**: Moving a task pins it to a new date but doesn't affect dependents.

---

## Using the Gantt Chart

### Chart Controls

Located above the chart:

| Control | Function |
|---------|----------|
| **Zoom: Auto** | Automatically selects best zoom level |
| **Zoom: Day** | Show individual days |
| **Zoom: Week** | Show weekly intervals |
| **Zoom: Month** | Show monthly intervals |
| **Show Today** | Toggle the red "Today" line |
| **Go to Today** | Scroll chart to current date |

### Today Marker

A red vertical line labeled "Today" shows the current date on the chart (when enabled and visible in the date range).

### Viewing Modes

Toggle in Project Settings:

- **Show Stages View**: Display individual stages within each task bar
- **Show Dependencies**: Display arrow lines between dependent tasks

### Interacting with the Chart

#### Hovering
Hover over any task bar to see a tooltip with:
- Task name
- Date range
- Total duration
- Status
- Progress (stages completed)

#### Dragging Tasks
Click and drag a task bar to move it:
- The task gets a "pinned" start date
- Its dependency is cleared
- With Auto-Schedule enabled, dependents shift too

#### Resizing Tasks
Drag the right edge of a task bar to change its duration:
- In Stages View: Resizes the specific stage
- In Status View: Resizes the last stage

#### Double-Click
Double-click a task bar to open the Edit Task dialog.

### Legend

The legend shows stage colors (Stages View) or status colors (Status View):
- **Drag the legend** to reposition it
- `File → Reset Legend Position` to restore default location

---

## Stages and Status

### What are Stages?

Stages are sub-tasks within a main task. Default stages:
- **Preparation** (orange)
- **Implementation** (blue)
- **Training/Adoption** (green)

Each stage has:
- **Duration**: Number of work days (supports decimals like 0.5)
- **Status**: Not Started, In Progress, or Completed

### Managing Stages

`File → Manage Stages...`

From here you can:
- Add new stage types
- Rename stages
- Change stage colors
- Remove stages (removes from all tasks)

### Status Colors

| Status | Color | Meaning |
|--------|-------|---------|
| Not Started | Red | Work hasn't begun |
| In Progress | Blue | Currently being worked on |
| Completed | Green | Finished |

### Aggregate Status

Parent tasks show an aggregate status:
- **Completed**: All stages are completed
- **Not Started**: All stages are not started
- **In Progress**: Mix of statuses

---

## Filtering and Sorting

Located above the task list:

### Filter

Filter tasks by their aggregate status:
- **All**: Show all tasks
- **Not Started**: Only tasks with no progress
- **In Progress**: Only tasks with partial progress
- **Completed**: Only fully completed tasks

The status bar shows "Showing X of Y tasks" when filtered.

**Note**: The Gantt chart always shows all tasks to maintain dependency accuracy.

### Sort

Sort tasks by:
- **Order Added**: Original order (default)
- **Start Date**: Earliest start date first
- **Name (A-Z)**: Alphabetical order
- **Duration**: Longest tasks first

---

## Saving and Exporting

### Save Project

`File → Save Project As...`

Saves as a `.gantt` file containing:
- Project name and start date
- All tasks with dates, dependencies, and statuses
- Stage configuration
- Legend position
- Auto-schedule preference

### Save as Template

`File → Save Project as Template...`

Saves as a `.gantt_template` file containing:
- Task names and dependencies
- Stage structure
- All statuses reset to "Not Started"
- No specific dates

Use templates for repeatable project types.

### Export Chart

`File → Export Chart...`

Export the Gantt chart as:
- **PNG**: High-resolution image (300 DPI)
- **PDF**: Vector document
- **SVG**: Scalable vector graphic

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Enter** | Edit selected task (opens dialog) |
| **Delete** / **Backspace** | Remove selected task (with confirmation) |
| **Tab** | Move focus to Quick Add box |
| **Escape** | Cancel inline editing |
| **Double-click** | Edit cell inline |

### Quick Add Box
| Key | Action |
|-----|--------|
| **Enter** | Add the task |
| **Tab** | Add the task |

---

## Tips and Best Practices

### For Fast Task Entry

1. Click the Quick Add box (or press Tab from the tree)
2. Type task name, press Enter
3. Repeat for all tasks
4. Then go back and set dependencies/durations

### For Accurate Scheduling

1. Set your Project Start Date first
2. Add all tasks without dependencies
3. Set dependencies to create the critical path
4. Adjust durations as needed
5. Enable Auto-Schedule for easy rescheduling

### For Large Projects

- Use **Filter** to focus on specific statuses
- Use **Sort by Start Date** to see chronological order
- Toggle off **Show Stages View** for a cleaner overview
- Zoom out to **Month** view for the big picture

### Working Days

The app automatically:
- Counts only Monday-Friday as work days
- Skips weekends when calculating dates
- Moves tasks starting on weekends to Monday

### Date Format

Always use **DD-MM-YYYY** format:
- ✅ `25-01-2026`
- ❌ `01/25/2026`
- ❌ `2026-01-25`

---

## Troubleshooting

### "Invalid Date" Error
Make sure dates are in DD-MM-YYYY format (e.g., 25-01-2026).

### Tasks Not Showing
Check the Filter dropdown - it might be filtering out tasks.

### Dependency Cycle Error
You have tasks that depend on each other in a loop. The error message shows the cycle. Remove one dependency to break the loop.

### Chart Not Updating
The chart updates automatically. If it seems stuck, try:
1. Click in another field
2. Press Enter to confirm any pending edits

### Unsaved Changes Indicator
The orange "● Unsaved changes" in the status bar means you have changes that haven't been saved. Use `File → Save Project As...` to save.

---

## File Formats

| Extension | Purpose |
|-----------|---------|
| `.gantt` | Full project file (dates, statuses, everything) |
| `.gantt_template` | Reusable template (no dates, statuses reset) |
| `.png`, `.pdf`, `.svg` | Exported chart images |

---

## Requirements

- Python 3.8+
- tkinter (usually included with Python)
- matplotlib
- pandas (for CSV/Excel import)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Support

For issues or feature requests, please contact your system administrator or refer to the project repository.
