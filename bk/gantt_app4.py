import tkinter as tk
from tkinter import ttk, simpledialog, filedialog
from datetime import datetime, timedelta
import math
import json
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Patch, ConnectionPatch
import copy
import collections

# --- Default Data ---

# This is now just the default template for a new project.
default_tasks_data = [
    {
        "name": "App Locker Creation & Testing",
        "depends_on": None,
        "start_date_override": None,
        "sub_tasks": [
            {"name": "Preparation", "duration": 0.5, "status": "In Progress"},
            {"name": "Implementation", "duration": 1, "status": "Not Started"},
            {"name": "Training/Adoption", "duration": 0.5, "status": "Not Started"}
        ]
    },
    {
        "name": "Conditional Access Design & Rollout",
        "depends_on": None,
        "start_date_override": None,
        "sub_tasks": [
            {"name": "Preparation", "duration": 1, "status": "In Progress"},
            {"name": "Implementation", "duration": 3, "status": "In Progress"},
            {"name": "Training/Adoption", "duration": 1, "status": "Not Started"}
        ]
    },
    {
        "name": "MFA Design & Rollout",
        "depends_on": "Conditional Access Design & Rollout",
        "start_date_override": None,
        "sub_tasks": [
            {"name": "Preparation", "duration": 0.5, "status": "In Progress"},
            {"name": "Implementation", "duration": 1, "status": "Not Started"},
            {"name": "Training/Adoption", "duration": 0.5, "status": "Not Started"}
        ]
    },
    {
        "name": "Workflow Walk through - Teams Call",
        "depends_on": "App Locker Creation & Testing",
        "start_date_override": None,
        "sub_tasks": [
            {"name": "Implementation", "duration": 0.25, "status": "Not Started"}
        ]
    },
    {
        "name": "Deploy Barracuda Cloud to Cloud Backup",
        "depends_on": "Workflow Walk through - Teams Call",
        "start_date_override": None,
        "sub_tasks": [
            {"name": "Preparation", "duration": 0.5, "status": "Not Started"},
            {"name": "Implementation", "duration": 1, "status": "Not Started"},
            {"name": "Training/Adoption", "duration": 0.5, "status": "Not Started"}
        ]
    },
    {
        "name": "Deploy Barracuda Email Security",
        "depends_on": "Workflow Walk through - Teams Call",
        "start_date_override": None,
        "sub_tasks": [
            {"name": "Preparation", "duration": 0.5, "status": "Not Started"},
            {"name": "Implementation", "duration": 1, "status": "Not Started"},
            {"name": "Training/Adoption", "duration": 0.5, "status": "Not Started"}
        ]
    }
]

status_colors = {
    'In Progress': '#4f81bd',
    'Not Started': '#c0504d',
    'Completed': '#5cb85c'
}

stage_colors = collections.OrderedDict([
    ('Preparation', '#f0ad4e'),
    ('Implementation', '#5bc0de'),
    ('Training/Adoption', '#5cb85c'),
])

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


class EditTaskDialog(simpledialog.Dialog):
    def __init__(self, parent, title, task_data, calculated_task_data, all_task_names, project_start_date):
        self.task_data_original = task_data
        self.task_data_copy = copy.deepcopy(task_data)
        self.calculated_task_data = calculated_task_data
        self.all_task_names = all_task_names
        self.project_start_date = project_start_date # Store for fallback
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        main_frame = ttk.LabelFrame(master, text="Task Properties", padding=10)
        main_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(main_frame, text="Task Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.name_var = tk.StringVar(value=self.task_data_copy['name'])
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(main_frame, text="Depends On:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        dependency_options = ["None"] + [name for name in self.all_task_names if name != self.task_data_original['name']]
        self.dependency_var = tk.StringVar(value=self.task_data_copy.get('depends_on') or "None")
        dep_cb = ttk.Combobox(main_frame, textvariable=self.dependency_var, values=dependency_options, width=37)
        dep_cb.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(main_frame, text="Start Date Override:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.start_date_var = tk.StringVar(value=self.task_data_copy.get('start_date_override') or "")
        start_date_entry = ttk.Entry(main_frame, textvariable=self.start_date_var, width=40)
        start_date_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(main_frame, text="End Date Override:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.end_date_override_var = tk.StringVar(value=self.task_data_copy.get('end_date_override') or "")
        end_date_entry = ttk.Entry(main_frame, textvariable=self.end_date_override_var, width=40)
        end_date_entry.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        end_date_entry.bind('<FocusOut>', self._on_task_end_date_change)

        self.stages_frame = ttk.LabelFrame(master, text="Stages", padding=10)
        self.stages_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(self.stages_frame,
                  text="Note: End Dates are based on the last calculation and may not reflect changes to dependencies above.",
                  font=("Arial", 8, "italic"), justify=tk.LEFT).pack(pady=(0, 5), fill=tk.X)

        self._build_stages_ui()
        
        return name_entry

    def _get_task_start_date(self):
        """Robustly gets the start date for the task for calculations within the dialog."""
        # Priority 1: Manual start date override from the dialog's own entry field
        start_override_str = self.start_date_var.get()
        if start_override_str:
            try:
                return datetime.strptime(start_override_str, "%d-%m-%Y")
            except ValueError:
                pass # Fall through if format is invalid

        # Priority 2: The already-calculated start date from the main app
        if self.calculated_task_data and self.calculated_task_data.get('start'):
            return self.calculated_task_data['start']
        
        # Priority 3: The project's global start date
        try:
            return datetime.strptime(self.project_start_date, "%d-%m-%Y")
        except (ValueError, TypeError):
            return datetime.now() # Final fallback

    def _build_stages_ui(self):
        for widget in self.stages_frame.winfo_children():
            if isinstance(widget, ttk.Frame) or isinstance(widget, ttk.Button):
                 widget.destroy()

        grid_frame = ttk.Frame(self.stages_frame)
        grid_frame.pack(fill=tk.X, expand=True)

        self.sub_task_vars = []
        status_options = list(status_colors.keys())

        ttk.Label(grid_frame, text="Stage Name", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(grid_frame, text="Duration", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(grid_frame, text="End Date", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5)
        ttk.Label(grid_frame, text="Status", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5)
        
        for i, sub_task in enumerate(self.task_data_copy.get('sub_tasks', [])):
            row = i + 1
            ttk.Label(grid_frame, text=sub_task['name']).grid(row=row, column=0, sticky="w", padx=5)
            duration_var = tk.DoubleVar(value=sub_task['duration'])
            duration_entry = ttk.Entry(grid_frame, textvariable=duration_var, width=10)
            duration_entry.grid(row=row, column=1, padx=5)
            
            end_date_var = tk.StringVar()
            end_date_entry = ttk.Entry(grid_frame, textvariable=end_date_var, width=12)
            end_date_entry.grid(row=row, column=2, padx=5)

            duration_entry.bind('<FocusOut>', lambda e, idx=i: self._on_duration_change(idx))
            end_date_entry.bind('<FocusOut>', lambda e, idx=i: self._on_end_date_change(idx))

            status_var = tk.StringVar(value=sub_task['status'])
            status_cb = ttk.Combobox(grid_frame, textvariable=status_var, values=status_options, state="readonly", width=15)
            status_cb.grid(row=row, column=3, padx=5)
            
            remove_btn = ttk.Button(grid_frame, text="X", width=2, command=lambda st=sub_task: self._remove_stage(st))
            remove_btn.grid(row=row, column=4, padx=5)

            self.sub_task_vars.append({'duration_var': duration_var, 'end_date_var': end_date_var, 'status_var': status_var})
        
        self._update_stage_display()

        action_frame = ttk.Frame(self.stages_frame)
        action_frame.pack(pady=10)
        
        current_stage_names = {st['name'] for st in self.task_data_copy.get('sub_tasks', [])}
        available_stages = [name for name in stage_colors.keys() if name not in current_stage_names]
        
        self.add_stage_var = tk.StringVar()
        add_stage_cb = ttk.Combobox(action_frame, textvariable=self.add_stage_var, values=available_stages, state="readonly", width=20)
        add_stage_cb.pack(side=tk.LEFT, padx=5)
        if not available_stages: add_stage_cb.config(state="disabled")

        add_btn = ttk.Button(action_frame, text="Add Stage", command=self._add_stage)
        add_btn.pack(side=tk.LEFT)
        if not available_stages: add_btn.config(state="disabled")

    def _update_stage_display(self):
        """A simple and direct function to refresh all stage end-date fields
        based on the current values in the duration fields."""
        try:
            task_start_date = self._get_task_start_date()
            cumulative_duration = 0.0
            for i, sub_task_ui in enumerate(self.sub_task_vars):
                duration = sub_task_ui['duration_var'].get()
                
                stage_start = add_work_days(task_start_date, cumulative_duration)
                stage_end = add_work_days(stage_start, duration)
                sub_task_ui['end_date_var'].set(stage_end.strftime("%d-%m-%Y"))
                
                cumulative_duration += duration
        except (tk.TclError, ValueError):
            return

    def _on_task_end_date_change(self, event=None):
        try:
            task_start_date = self._get_task_start_date()
            end_date_str = self.end_date_override_var.get()
            if not end_date_str: return
            end_date = datetime.strptime(end_date_str, "%d-%m-%Y")
            if end_date < task_start_date: return

            # 1. Calculate new proportional durations
            total_days = float(count_work_days(task_start_date, end_date))
            sub_tasks = self.task_data_copy.get('sub_tasks', [])
            num_stages = len(sub_tasks)
            if num_stages == 0: return

            base_duration = total_days / num_stages
            durations = [round(base_duration, 2)] * num_stages
            remainder = round(total_days - sum(durations), 2)
            if durations:
                durations[0] = round(durations[0] + remainder, 2)

            # 2. Update the UI duration fields and the underlying data model
            for i, sub_task_data in enumerate(sub_tasks):
                new_duration = durations[i]
                if new_duration < 0: new_duration = 0
                sub_task_data['duration'] = new_duration
                self.sub_task_vars[i]['duration_var'].set(new_duration)
            
            # 3. Update the UI end date fields based on the new durations
            self._update_stage_display()

        except (ValueError, tk.TclError):
            return
    
    def _on_duration_change(self, index):
        # A manual change to duration just pushes subsequent tasks.
        self._update_stage_display()

    def _on_end_date_change(self, index):
        # A manual change to an end date calculates a new duration for that stage,
        # then pushes subsequent tasks.
        try:
            sub_task_vars = self.sub_task_vars[index]
            end_date = datetime.strptime(sub_task_vars['end_date_var'].get(), "%d-%m-%Y")
            
            task_start_date = self._get_task_start_date()
            predecessor_duration = 0
            for i in range(index):
                predecessor_duration += self.sub_task_vars[i]['duration_var'].get()
            
            start_date = add_work_days(task_start_date, predecessor_duration)

            if end_date < start_date:
                self._update_stage_display() # Revert to original if date is invalid
                return

            duration = count_work_days(start_date, end_date)
            sub_task_vars['duration_var'].set(float(duration))
        except (ValueError, tk.TclError):
            pass
        
        self._update_stage_display()

    def _add_stage(self):
        stage_to_add = self.add_stage_var.get()
        if stage_to_add:
            new_stage = {
                "name": stage_to_add,
                "duration": 1,
                "status": "Not Started"
            }
            if 'sub_tasks' not in self.task_data_copy:
                self.task_data_copy['sub_tasks'] = []
            self.task_data_copy['sub_tasks'].append(new_stage)
            self._build_stages_ui()

    def _remove_stage(self, sub_task_to_remove):
        self.task_data_copy['sub_tasks'].remove(sub_task_to_remove)
        self._build_stages_ui()

    def apply(self):
        self.task_data_copy['name'] = self.name_var.get()
        dep = self.dependency_var.get()
        self.task_data_copy['depends_on'] = dep if dep != "None" else None
        override = self.start_date_var.get()
        self.task_data_copy['start_date_override'] = override if override else None
        end_override = self.end_date_override_var.get()
        self.task_data_copy['end_date_override'] = end_override if end_override else None
        
        # Update sub_tasks from the UI widgets before finishing
        new_sub_tasks = []
        for i, sub_task_ui in enumerate(self.sub_task_vars):
            original_sub_task = self.task_data_copy['sub_tasks'][i]
            new_sub_tasks.append({
                "name": original_sub_task['name'],
                "duration": sub_task_ui['duration_var'].get(),
                "status": sub_task_ui['status_var'].get(),
                "start_date_override": original_sub_task.get('start_date_override')
            })
        self.task_data_copy['sub_tasks'] = new_sub_tasks

        self.task_data_original.clear()
        self.task_data_original.update(self.task_data_copy)
        
        self.result = True


class ManageStagesDialog(simpledialog.Dialog):
    def __init__(self, parent, title, stages_data):
        self.stages_data_original = stages_data
        self.stages_data_copy = copy.deepcopy(stages_data)
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        self.stages_frame = ttk.Frame(master, padding=10)
        self.stages_frame.pack(fill="both", expand=True)
        self._build_stages_ui()
        return self.stages_frame

    def _build_stages_ui(self):
        for widget in self.stages_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.stages_frame, text="Stage Name", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5)
        ttk.Label(self.stages_frame, text="Color", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5)

        row = 1
        self.stage_vars = collections.OrderedDict()
        for name, color in self.stages_data_copy.items():
            name_var = tk.StringVar(value=name)
            color_var = tk.StringVar(value=color)
            self.stage_vars[name] = {'name_var': name_var, 'color_var': color_var}

            name_entry = ttk.Entry(self.stages_frame, textvariable=name_var)
            name_entry.grid(row=row, column=0, padx=5, pady=2)
            
            color_entry = ttk.Entry(self.stages_frame, textvariable=color_var)
            color_entry.grid(row=row, column=1, padx=5, pady=2)

            remove_btn = ttk.Button(self.stages_frame, text="X", width=2, command=lambda n=name: self._remove_stage(n))
            remove_btn.grid(row=row, column=2, padx=5, pady=2)
            row += 1

        add_btn = ttk.Button(self.stages_frame, text="Add New Stage", command=self._add_stage)
        add_btn.grid(row=row, column=0, columnspan=3, pady=10)

    def _add_stage(self):
        new_name = simpledialog.askstring("Add Stage", "Enter new stage name:", parent=self)
        if new_name and new_name not in self.stages_data_copy:
            self.stages_data_copy[new_name] = '#cccccc' # Default color
            self._build_stages_ui()

    def _remove_stage(self, name):
        if name in self.stages_data_copy:
            del self.stages_data_copy[name]
            del self.stage_vars[name]
            self._build_stages_ui()

    def apply(self):
        # Read the potentially changed names and colors from the UI
        final_stages = collections.OrderedDict()
        for original_name, vars in self.stage_vars.items():
            new_name = vars['name_var'].get()
            new_color = vars['color_var'].get()
            
            if not new_name: continue # Don't save a stage with no name
            
            final_stages[new_name] = {
                "color": new_color,
                "original_name": original_name
            }
        self.result = final_stages


# --- GUI Application ---

class GanttChartApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gantt Chart Planner")
        self.geometry("1800x800")
        
        self._is_updating = False
        self.controls_visible = True
        self._drag_data = None
        self.project_name_var = tk.StringVar(value="New Project")
        self.show_stages_var = tk.BooleanVar(value=True)
        self.show_dependencies_var = tk.BooleanVar(value=True)
        self.chart_items = []
        self._tree_drag_data = {}
        self._link_mode_enabled = False
        self._link_start_item = None
        self.style = ttk.Style()
        self.style.configure('Accent.TButton', relief=tk.SUNKEN)
        self._highlighted_patches = {} # For hover effects
        self.current_filepath = None
        self.view_mode = 'daily'

        # --- Menu Bar ---
        self.create_menu()

        # --- Main Layout ---
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.control_frame = ttk.Frame(self.main_frame, width=700, padding="10")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        
        # Separator and toggle button
        self.separator_frame = ttk.Frame(self.main_frame, width=20)
        self.separator_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.toggle_button = ttk.Button(self.separator_frame, text="<", command=self.toggle_controls, width=2)
        self.toggle_button.pack(pady=20)
        
        self.chart_frame = ttk.Frame(self.main_frame)
        self.chart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # --- App State ---
        self.tasks_data = []
        self.task_rows = {} 

        # --- Initialization ---
        self.setup_chart_canvas()
        self.build_controls()
        self.new_blank_project() # Start with a blank project
        self.connect_drag_events()

    def connect_drag_events(self):
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)

    def on_press(self, event):
        if event.inaxes != self.ax: return

        if self._link_mode_enabled:
            clicked_item = None
            for item in reversed(self.chart_items):
                if item['level'] != 0: continue # Can only link parent tasks
                patch = item.get('patch')
                if patch and patch.contains(event)[0]:
                    clicked_item = item
                    break
            
            if clicked_item:
                if not self._link_start_item:
                    # This is the first click, defining the predecessor
                    self._link_start_item = clicked_item
                    # Maybe add a visual cue here, like changing the bar color
                else:
                    # This is the second click, defining the successor and creating the link
                    start_task = self._link_start_item['data']
                    end_task = clicked_item['data']

                    if start_task is not end_task:
                        end_task['depends_on'] = start_task['name']
                        end_task['start_date_override'] = None # Dependency takes precedence
                        self.calculate_and_draw()

                    # Reset and exit link mode
                    self.toggle_link_mode()
            return

        if event.dblclick:
            clicked_item = None
            for item in reversed(self.chart_items):
                patch = item.get('patch')
                if patch is None: continue
                contains, _ = patch.contains(event)
                if contains:
                    clicked_item = item
                    break
            
            if clicked_item:
                parent_task_data = clicked_item.get('parent_task', clicked_item.get('data'))
                for i, task_in_list in enumerate(self.tasks_data):
                    if task_in_list is parent_task_data:
                        item_id = f"task_{i}"
                        self.edit_task(item_id=item_id)
                        break
            return

        # Iterate in reverse to check sub-tasks (drawn on top) first
        for item in reversed(self.chart_items):
            patch = item.get('patch')
            if patch is None: continue

            contains, _ = patch.contains(event)
            if contains:
                level = item['level']
                is_stages_view = self.show_stages_var.get()
                
                drag_mode = None
                bar_right_edge = patch.get_x() + patch.get_width()
                resize_threshold = 0.5

                if is_stages_view:
                    # In stages view: can resize or move sub-tasks, or move parent tasks
                    if level == 1:
                        if abs(event.xdata - bar_right_edge) < resize_threshold:
                            drag_mode = "resize"
                        else:
                            drag_mode = "move"
                    elif level == 0:
                        drag_mode = "move"
                else:
                    # In status view: can move or resize the whole task
                    if abs(event.xdata - bar_right_edge) < resize_threshold:
                        drag_mode = "resize"
                    else:
                        drag_mode = "move"

                if drag_mode:
                    task_data = item['data']
                    self._drag_data = {
                        "item": item,
                        "x_offset": event.xdata - patch.get_x(),
                        "mode": drag_mode
                    }
                    
                    if drag_mode == 'resize' and not is_stages_view:
                        # For resizing parent task, store original durations in days
                        self._drag_data['original_total_duration'] = sum(st.get('duration', 0) for st in task_data.get('sub_tasks', []))
                        self._drag_data['original_last_sub_duration'] = task_data['sub_tasks'][-1]['duration'] if task_data.get('sub_tasks') else 0
                    else:
                        # For other modes, store patch width
                        self._drag_data["patch_original_width"] = patch.get_width()

                    cursor = "sb_h_double_arrow" if drag_mode == "resize" else "hand2"
                    self.canvas.get_tk_widget().config(cursor=cursor)
                    return

    def on_motion(self, event):
        if self._drag_data is not None:
            # --- Dragging Logic ---
            item = self._drag_data["item"]
            task_data = item["data"]
            patch = item["patch"]
            mode = self._drag_data["mode"]
            is_stages_view = self.show_stages_var.get()

            if mode == "resize":
                if event.xdata is None: return # Prevent error if mouse leaves axes

                # The coordinate system is always in workdays, so no need to scale by view_mode.
                new_duration = event.xdata - patch.get_x()
                new_duration = round(new_duration * 4) / 4
                if new_duration < 0.25: new_duration = 0.25
                
                if is_stages_view:
                    # Resize the specific sub-task (stage). The `calculate_task_dates` function
                    # will handle pushing subsequent tasks automatically.
                    task_data['duration'] = new_duration
                else:
                    # Resize the parent task by adjusting its last sub-task
                    # Calculate new total duration in days based on mouse position
                    new_total_duration = event.xdata - patch.get_x()

                    new_total_duration = round(new_total_duration * 4) / 4
                    if new_total_duration < 0.25: new_total_duration = 0.25

                    # Calculate the change relative to the drag start
                    delta_duration = new_total_duration - self._drag_data["original_total_duration"]
                    
                    if task_data.get('sub_tasks'):
                        last_sub_task = task_data['sub_tasks'][-1]
                        # Apply the delta to the last sub-task's original duration
                        new_sub_duration = self._drag_data["original_last_sub_duration"] + delta_duration
                        if new_sub_duration < 0.25: new_sub_duration = 0.25
                        last_sub_task['duration'] = new_sub_duration

                self.on_ui_change()

            elif mode == "move":
                if event.xdata is None: return 

                if item['level'] == 1 and is_stages_view:
                    # --- Logic for moving a sub-task (stage) ---
                    parent_task = item['parent_task']
                    sub_task_index = parent_task['sub_tasks'].index(task_data)

                    # Calculate the delta of the drag in days. Coords are always workdays.
                    new_start_coord = event.xdata - self._drag_data["x_offset"]
                    original_start_coord = patch.get_x()
                    delta_days = new_start_coord - original_start_coord
                    
                    if abs(delta_days) < 0.1: return # Ignore tiny movements

                    # If the parent task has a fixed end date, we rebalance durations
                    # instead of pushing the end date out.
                    if parent_task.get("end_date_override"):
                        # --- Rebalancing Logic ---
                        if 'original_current_duration' not in self._drag_data:
                            self._drag_data['original_current_duration'] = task_data['duration']

                        if sub_task_index > 0:
                            # Dragging a middle stage: rebalance with the PREVIOUS one.
                            prev_sub_task = parent_task['sub_tasks'][sub_task_index - 1]
                            if 'original_prev_duration' not in self._drag_data:
                                self._drag_data['original_prev_duration'] = prev_sub_task['duration']

                            new_prev_duration = self._drag_data['original_prev_duration'] + delta_days
                            new_current_duration = self._drag_data['original_current_duration'] - delta_days
                            
                            new_prev_duration = round(new_prev_duration * 4) / 4
                            new_current_duration = round(new_current_duration * 4) / 4

                            if new_prev_duration >= 0.25 and new_current_duration >= 0.25:
                                prev_sub_task['duration'] = new_prev_duration
                                task_data['duration'] = new_current_duration
                        
                        else: # Dragging the FIRST stage (index 0)
                            # This moves the whole task's start date, but steals duration from
                            # the first stage to preserve the overall end date.
                            new_start_index = int(round(event.xdata - self._drag_data["x_offset"]))
                            if 0 <= new_start_index < len(self.work_days):
                                new_start_date = self.work_days[new_start_index]
                            else: 
                                return
                            
                            parent_task['start_date_override'] = new_start_date.strftime("%d-%m-%Y")
                            parent_task['depends_on'] = None

                            new_current_duration = self._drag_data['original_current_duration'] - delta_days
                            new_current_duration = round(new_current_duration * 4) / 4

                            if new_current_duration >= 0.25:
                                task_data['duration'] = new_current_duration
                        
                        self.on_ui_change()

                    else:
                        # --- Original "Push" Logic ---
                        if sub_task_index > 0:
                            prev_sub_task = parent_task['sub_tasks'][sub_task_index - 1]
                            
                            if 'original_prev_duration' not in self._drag_data:
                                self._drag_data['original_prev_duration'] = prev_sub_task['duration']

                            new_prev_duration = self._drag_data['original_prev_duration'] + delta_days
                            rounded_duration = round(new_prev_duration * 4) / 4
                            if rounded_duration < 0.25: rounded_duration = 0.25
                            prev_sub_task['duration'] = rounded_duration
                            
                        else:
                            # Moving the first sub-task pins the parent task.
                            new_start_index = int(round(event.xdata - self._drag_data["x_offset"]))
                            if 0 <= new_start_index < len(self.work_days):
                                new_start_date = self.work_days[new_start_index]
                            else: 
                                return
                            
                            parent_task['start_date_override'] = new_start_date.strftime("%d-%m-%Y")
                            parent_task['depends_on'] = None

                        self.on_ui_change()

                else:
                    # --- Logic for moving a parent task ---
                    # Convert x-coordinate (workday index) back to a date.
                    new_start_index = int(round(event.xdata - self._drag_data["x_offset"]))
                    if 0 <= new_start_index < len(self.work_days):
                        new_start_date = self.work_days[new_start_index]
                    else:
                        return # Out of bounds

                    # This part is common for both views
                    parent_task = item.get('parent_task', task_data)
                    parent_task['start_date_override'] = new_start_date.strftime("%d-%m-%Y")
                    parent_task['depends_on'] = None
                    self.on_ui_change()
            return

        # --- Hover Logic ---
        if event.inaxes != self.ax:
            if self._highlighted_patches:
                for patch, style in self._highlighted_patches.items():
                    patch.update(style)
                self._highlighted_patches.clear()
                self.canvas.draw_idle()
            self.canvas.get_tk_widget().config(cursor="")
            return
        
        # Reset previously highlighted items before finding new ones
        for patch, style in self._highlighted_patches.items():
            patch.update(style)
        self._highlighted_patches.clear()

        # Find what is being hovered over
        hovered_item = None
        for item in reversed(self.chart_items):
            patch = item.get('patch')
            if patch and patch.contains(event)[0]:
                hovered_item = item
                break
        
        if hovered_item:
            # Find the top-level parent task to highlight its connections
            parent_task_item = hovered_item
            if hovered_item['level'] != 0:
                parent_task_item = next((i for i in self.chart_items if i.get('level') == 0 and i['data'] is hovered_item.get('parent_task')), None)

            if parent_task_item:
                # Highlight the main task bar
                main_patch = parent_task_item.get('patch')
                if main_patch:
                    self._highlighted_patches[main_patch] = {'facecolor': main_patch.get_facecolor(), 'edgecolor': main_patch.get_edgecolor()}
                    main_patch.set_facecolor('#d9edf7') # Light blue highlight
                    main_patch.set_edgecolor('#31708f')

                # Highlight dependency lines and connected tasks
                for con_patch in parent_task_item['data'].get('connections', []):
                    self._highlighted_patches[con_patch] = {'color': con_patch.get_edgecolor(), 'lw': con_patch.get_linewidth()}
                    con_patch.set_color('#31708f')
                    con_patch.set_linewidth(2.0)

        self.canvas.draw_idle()

        # --- Cursor Logic ---
        cursor = ""
        is_stages_view = self.show_stages_var.get()
        resize_threshold = 0.5
        
        for item in reversed(self.chart_items):
            patch = item.get('patch')
            if patch is None: continue
            contains, _ = patch.contains(event)
            
            if contains:
                level = item['level']
                bar_right_edge = patch.get_x() + patch.get_width()
                
                can_resize = (is_stages_view and level == 1) or (not is_stages_view and level == 0)
                can_move = (is_stages_view and level == 1) or (is_stages_view and level == 0) or (not is_stages_view)

                if can_resize and abs(event.xdata - bar_right_edge) < resize_threshold:
                    cursor = "sb_h_double_arrow"
                elif can_move:
                    cursor = "hand2"
                
                break 

        self.canvas.get_tk_widget().config(cursor=cursor)

    def on_release(self, event):
        # End the drag operation and reset cursor
        self._drag_data = None
        self.canvas.get_tk_widget().config(cursor="")
        # Trigger a final hover check to set cursor correctly if still over a bar
        self.on_motion(event)

    def toggle_controls(self):
        if self.controls_visible:
            self.control_frame.pack_forget()
            self.toggle_button.config(text=">")
            self.controls_visible = False
        else:
            self.control_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, before=self.separator_frame)
            self.toggle_button.config(text="<")
            self.controls_visible = True

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        file_menu.add_command(label="New Blank Project", command=self.new_blank_project)
        file_menu.add_command(label="Load Template", command=self.load_template)
        file_menu.add_separator()
        file_menu.add_command(label="Open Project...", command=self.open_project)
        file_menu.add_command(label="Save Project As...", command=self.save_project_as)
        file_menu.add_command(label="Save Project as Template...", command=self.save_project_as_template)
        file_menu.add_command(label="Export Chart...", command=self.export_chart)
        file_menu.add_separator()
        file_menu.add_command(label="Manage Stages...", command=self.manage_stages)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

    def setup_chart_canvas(self):
        self.figure = Figure(figsize=(18, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self.chart_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def on_dependency_change(self, event, task):
        """Called specifically when a dependency dropdown is changed."""
        # If a dependency is chosen, we must clear the manual start date to "un-pin" it.
        if task['ui_dependency_var'].get() != "None":
            task['ui_start_date_override_var'].set("")
        
        # Now, trigger the standard update process.
        self.on_ui_change(event)

    def on_ui_change(self, event=None):
        if self._is_updating: return
        self._is_updating = True
        try:
            # name_changed = self.sync_ui_to_data() # Data is now synced differently or not at all
            # if name_changed:
            self.update_window_title()
            self.populate_treeview() # Re-populating is now the main update path
            self.calculate_and_draw()
        finally:
            self._is_updating = False

    def update_window_title(self):
        project_name = self.project_name_var.get()
        if self.current_filepath:
            self.title(f"{project_name} - {self.current_filepath}")
        else:
            self.title(f"{project_name} - Gantt Chart Planner")

    def new_blank_project(self):
        self.tasks_data = []
        self.project_name_var.set("New Project")
        self.current_filepath = None
        self.populate_treeview()
        self.calculate_and_draw()
        self.update_window_title()

    def load_template(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Gantt Template Files", "*.gantt_template"), ("All Files", "*.*")],
            title="Load Project from Template"
        )
        if not filepath:
            return

        with open(filepath, 'r') as f:
            template_data = json.load(f)
        
        global stage_colors
        
        # Load tasks from the template
        self.tasks_data = copy.deepcopy(template_data["tasks"])
        
        # Load stages from the template, updating the global definition
        if "stages" in template_data:
            if isinstance(template_data["stages"], dict): # old format
                stage_colors = collections.OrderedDict(template_data["stages"].items())
            else: # new format: list of [key, value]
                stage_colors = collections.OrderedDict(template_data["stages"])

        # Set a default start date for the new project
        self.project_start_date_var.set(datetime.now().strftime("%d-%m-%Y"))
        
        self.project_name_var.set("New Project from Template")
        self.current_filepath = None
        self.populate_treeview()
        self.calculate_and_draw()
        self.update_window_title()
        
    def open_project(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Gantt Project Files", "*.gantt"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        
        with open(filepath, 'r') as f:
            project_data = json.load(f)
            
        global stage_colors
        if "stages" in project_data:
            if isinstance(project_data["stages"], dict): # old format for backward compatibility
                stage_colors = collections.OrderedDict(project_data["stages"].items())
            else: # new format: list of [key, value]
                stage_colors = collections.OrderedDict(project_data["stages"])

        self.current_filepath = filepath
        self.project_name_var.set(project_data.get("project_name", "Untitled Project"))
        self.project_start_date_var.set(project_data["project_start_date"])
        self.tasks_data = project_data["tasks"]
        self.populate_treeview()
        self.calculate_and_draw()
        self.update_window_title()

    def save_project_as(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".gantt",
            filetypes=[("Gantt Project Files", "*.gantt"), ("All Files", "*.*")]
        )
        if not filepath:
            return
            
        # Create a clean, serializable copy of the tasks data for saving.
        # This removes calculated, non-serializable fields like datetime objects and plot items.
        tasks_to_save = copy.deepcopy(self.tasks_data)
        for task in tasks_to_save:
            task.pop('start', None)
            task.pop('end', None)
            task.pop('connections', None)
            for sub_task in task.get('sub_tasks', []):
                sub_task.pop('start', None)
                sub_task.pop('end', None)

        # Prepare data for saving
        project_data = {
            "project_name": self.project_name_var.get(),
            "project_start_date": self.project_start_date_var.get(),
            "tasks": tasks_to_save,
            "stages": list(stage_colors.items())
        }
        
        with open(filepath, 'w') as f:
            json.dump(project_data, f, indent=4)
        
        self.current_filepath = filepath
        self.update_window_title()

    def save_project_as_template(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".gantt_template",
            filetypes=[("Gantt Template Files", "*.gantt_template"), ("All Files", "*.*")],
            title="Save Project as Template"
        )
        if not filepath:
            return

        # Prepare a clean version of the tasks for the template
        template_tasks = []
        for task in self.tasks_data:
            clean_task = {
                "name": task["name"],
                "depends_on": task.get("depends_on"),
                "sub_tasks": []
            }
            if task.get("sub_tasks"):
                for sub_task in task["sub_tasks"]:
                    clean_sub_task = {
                        "name": sub_task["name"],
                        "duration": sub_task["duration"],
                        # Templates should always start as "Not Started"
                        "status": "Not Started"
                    }
                    clean_task["sub_tasks"].append(clean_sub_task)
            template_tasks.append(clean_task)

        template_data = {
            "tasks": template_tasks,
            "stages": list(stage_colors.items())
        }

        with open(filepath, 'w') as f:
            json.dump(template_data, f, indent=4)
        
        tk.messagebox.showinfo("Template Saved", f"Template successfully saved to\n{filepath}")

    def export_chart(self):
        if not self.tasks:
            tk.messagebox.showinfo("Export Chart", "There is nothing to export.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Export Gantt Chart",
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("PDF Document", "*.pdf"),
                ("SVG Vector Image", "*.svg"),
                ("All Files", "*.*")
            ]
        )
        if not filepath:
            return

        try:
            # We can pass bbox_inches='tight' to make sure labels are not cut off
            # A higher DPI ensures better quality for raster formats like PNG.
            self.figure.savefig(filepath, bbox_inches='tight', dpi=300)
            tk.messagebox.showinfo("Export Successful", f"Chart successfully saved to\n{filepath}")
        except Exception as e:
            tk.messagebox.showerror("Export Error", f"An error occurred while exporting the chart: {e}")

    def build_controls(self):
        for widget in self.control_frame.winfo_children():
            widget.destroy()

        settings_frame = ttk.LabelFrame(self.control_frame, text="Project Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)

        ttk.Label(settings_frame, text="Project Name:").grid(row=0, column=0, sticky="w")
        project_name_entry = ttk.Entry(settings_frame, textvariable=self.project_name_var)
        project_name_entry.grid(row=0, column=1, sticky="w", pady=2)
        project_name_entry.bind("<FocusOut>", self.on_ui_change)
        project_name_entry.bind("<Return>", self.on_ui_change)

        self.project_start_date_var = tk.StringVar(value=datetime.now().strftime("%d-%m-%Y"))
        ttk.Label(settings_frame, text="Project Start Date:").grid(row=1, column=0, sticky="w")
        start_date_entry = ttk.Entry(settings_frame, textvariable=self.project_start_date_var)
        start_date_entry.grid(row=1, column=1, sticky="w", pady=2)
        start_date_entry.bind("<FocusOut>", self.on_ui_change)
        start_date_entry.bind("<Return>", self.on_ui_change)

        ttk.Label(settings_frame, text="Show Stages View:").grid(row=2, column=0, sticky="w", pady=5)
        stages_toggle = ttk.Checkbutton(settings_frame, variable=self.show_stages_var, command=self.calculate_and_draw)
        stages_toggle.grid(row=2, column=1, sticky="w")
        
        ttk.Label(settings_frame, text="Show Dependencies:").grid(row=3, column=0, sticky="w", pady=5)
        deps_toggle = ttk.Checkbutton(settings_frame, variable=self.show_dependencies_var, command=self.calculate_and_draw)
        deps_toggle.grid(row=3, column=1, sticky="w")

        editor_frame = ttk.LabelFrame(self.control_frame, text="Tasks", padding="10")
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # --- Treeview for Tasks ---
        columns = ("duration", "status", "depends_on", "start_date_override")
        self.task_tree = ttk.Treeview(editor_frame, columns=columns, show="tree headings")
        
        self.task_tree.heading("#0", text="Task Name")
        self.task_tree.column("#0", width=250, anchor='w')
        
        self.task_tree.heading("duration", text="Duration")
        self.task_tree.column("duration", width=60, anchor='center')
        
        self.task_tree.heading("status", text="Status")
        self.task_tree.column("status", width=100, anchor='center')
        
        self.task_tree.heading("depends_on", text="Depends On")
        self.task_tree.column("depends_on", width=150, anchor='w')

        self.task_tree.heading("start_date_override", text="Start Date")
        self.task_tree.column("start_date_override", width=100, anchor='center')
        
        self.task_tree.pack(fill=tk.BOTH, expand=True)
        self.task_tree.bind("<Double-1>", self.on_tree_double_click)
        self.task_tree.bind("<ButtonPress-1>", self.on_tree_press)
        self.task_tree.bind("<B1-Motion>", self.on_tree_motion)
        self.task_tree.bind("<ButtonRelease-1>", self.on_tree_release)

        action_frame = ttk.Frame(self.control_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Add New Task", command=self.add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Edit Selected Task", command=self.edit_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Remove Selected Task", command=self.remove_task).pack(side=tk.LEFT, padx=5)
        self.link_button = ttk.Button(action_frame, text="Link Tasks", command=self.toggle_link_mode)
        self.link_button.pack(side=tk.LEFT, padx=5)

    def populate_treeview(self):
        # Clear existing items
        for i in self.task_tree.get_children():
            self.task_tree.delete(i)
        
        # Populate with new data
        for i, task_data in enumerate(self.tasks_data):
            task_id = self.task_tree.insert(
                "", "end", iid=f"task_{i}", text=task_data['name'], open=True,
                values=("", "", task_data.get('depends_on') or "", task_data.get('start_date_override') or "")
            )
            
            for j, sub_task in enumerate(task_data.get('sub_tasks', [])):
                self.task_tree.insert(
                    task_id, "end", iid=f"task_{i}_sub_{j}", text=f"  - {sub_task['name']}",
                    values=(sub_task['duration'], sub_task['status'], "", "")
                )

    def sync_ui_to_data(self):
        # This function is now more complex. For now, we assume the UI is read-only
        # and all data modifications happen through code/dialogs, then the tree is refreshed.
        return False

    def on_tree_double_click(self, event):
        """Handler for double-clicking an item in the tree."""
        self._tree_drag_data = {} # Cancel any drag operation
        
        # Check if the double click was on a task name
        column = self.task_tree.identify_column(event.x)
        if column == "#0": # The task name column
            iid = self.task_tree.identify_row(event.y)
            if iid and not self.task_tree.parent(iid): # Ensure it's a top-level task
                self._edit_task_name_inline(iid)
        else:
            # Fallback to opening the dialog for other columns or sub-tasks
            iid = self.task_tree.identify_row(event.y)
            if iid:
                self.edit_task(item_id=iid)

    def _edit_task_name_inline(self, iid):
        """Handle in-line editing of a task name."""
        bbox = self.task_tree.bbox(iid, "#0")
        if not bbox: return
        
        x, y, width, height = bbox
        
        original_name = self.task_tree.item(iid, "text")
        entry_var = tk.StringVar(value=original_name)
        entry = ttk.Entry(self.task_tree, textvariable=entry_var)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()
        
        def on_commit(event=None):
            new_name = entry_var.get()
            entry.destroy()
            
            if new_name and new_name != original_name:
                # Find the task in the data and update its name
                for task in self.tasks_data:
                    if task['name'] == original_name:
                        task['name'] = new_name
                        break
                
                # Update any dependencies pointing to the old name
                for task in self.tasks_data:
                    if task.get('depends_on') == original_name:
                        task['depends_on'] = new_name
                
                # Refresh the UI
                self.populate_treeview()
                self.calculate_and_draw()

        entry.bind("<Return>", on_commit)
        entry.bind("<FocusOut>", on_commit)

    def on_tree_press(self, event):
        """Start dragging an item in the tree."""
        iid = self.task_tree.identify_row(event.y)
        if not iid: return

        # Only allow dragging of top-level tasks, not sub-tasks (stages)
        parent_iid = self.task_tree.parent(iid)
        if not parent_iid:
            self._tree_drag_data = {"type": "task", "iid": iid}

    def on_tree_motion(self, event):
        """Move an item during drag."""
        if not self._tree_drag_data: return

        # This logic now only applies to top-level tasks
        drag_iid = self._tree_drag_data["iid"]
        target_iid = self.task_tree.identify_row(event.y)
        if not target_iid or target_iid == drag_iid: return

        if not self.task_tree.parent(target_iid): 
            target_index = self.task_tree.index(target_iid)
            self.task_tree.move(drag_iid, "", target_index)

    def on_tree_release(self, event):
        """Finalize the reordering of a dragged item."""
        if not self._tree_drag_data:
            return

        # This logic now only applies to top-level tasks
        new_task_order_iids = self.task_tree.get_children("")
        new_task_names = [self.task_tree.item(iid, "text") for iid in new_task_order_iids]
        
        tasks_dict = {task['name']: task for task in self.tasks_data}
        
        new_tasks_data_list = []
        for name in new_task_names:
            if name in tasks_dict:
                new_tasks_data_list.append(tasks_dict[name])
        
        self.tasks_data = new_tasks_data_list
        
        self._tree_drag_data = {} # End the drag operation
        self.on_ui_change() # Redraw everything

    def edit_task(self, item_id=None):
        selected_id = None
        if item_id:
            selected_id = item_id
        else:
            selected_item = self.task_tree.selection()
            if not selected_item:
                tk.messagebox.showwarning("Edit Task", "Please select a task to edit.")
                return
            selected_id = selected_item[0]

        if not selected_id:
            return
        
        parent_iid = self.task_tree.parent(selected_id)
        if parent_iid:
            selected_id = parent_iid

        task_name_to_edit = self.task_tree.item(selected_id, "text")
        task_to_edit = None
        for task in self.tasks_data:
            if task['name'] == task_name_to_edit:
                task_to_edit = task
                break

        calculated_task_data = None
        if hasattr(self, 'tasks'):
            for task in self.tasks:
                if task['name'] == task_name_to_edit:
                    calculated_task_data = task
                    break

        if task_to_edit:
            other_task_names = [t['name'] for t in self.tasks_data if t['name'] != task_name_to_edit]
            
            dialog = EditTaskDialog(self, "Edit Task", task_to_edit, calculated_task_data, other_task_names, self.project_start_date_var.get())
            
            if dialog.result:
                # If a task name was changed, we might need to update dependencies in other tasks
                new_name = dialog.task_data_copy['name']
                if task_name_to_edit != new_name:
                    for t in self.tasks_data:
                        if t.get('depends_on') == task_name_to_edit:
                            t['depends_on'] = new_name
                
                self.populate_treeview()
                self.calculate_and_draw()

    def add_task(self):
        new_task = {
            "name": f"New Task {len(self.tasks_data) + 1}",
            "depends_on": None,
            "start_date_override": None,
            "sub_tasks": [
                {"name": "Preparation", "duration": 1, "status": "Not Started"},
                {"name": "Implementation", "duration": 1, "status": "Not Started"},
                {"name": "Training/Adoption", "duration": 1, "status": "Not Started"}
            ]
        }
        # Filter the hardcoded list to only include stages that currently exist globally
        existing_stage_names = stage_colors.keys()
        new_task['sub_tasks'] = [st for st in new_task['sub_tasks'] if st['name'] in existing_stage_names]

        self.tasks_data.append(new_task)
        self.populate_treeview()
        self.calculate_and_draw()

    def remove_task(self):
        selected_item = self.task_tree.selection()
        if not selected_item:
            tk.messagebox.showwarning("Remove Task", "Please select a task to remove.")
            return

        selected_id = selected_item[0]
        
        # We only allow removing top-level tasks. Find which task it is.
        parent_iid = self.task_tree.parent(selected_id)
        if parent_iid: # It's a sub-task, find the top-level parent
            selected_id = parent_iid

        # Find the corresponding task data to remove
        task_name_to_remove = self.task_tree.item(selected_id, "text")
        task_to_remove = None
        for task in self.tasks_data:
            if task['name'] == task_name_to_remove:
                task_to_remove = task
                break
        
        if task_to_remove:
            # Go through all other tasks and remove any dependencies on the task being removed
            for other_task in self.tasks_data:
                if other_task.get('depends_on') == task_name_to_remove:
                    other_task['depends_on'] = None

            self.tasks_data.remove(task_to_remove)
            self.populate_treeview()
            self.calculate_and_draw()
        
    def calculate_and_draw(self):
        try:
            # self.sync_ui_to_data() # UI is read-only for now
            project_start_date_str = self.project_start_date_var.get()
            project_start_date = datetime.strptime(project_start_date_str, "%d-%m-%Y")
            
            if self.tasks_data:
                self.tasks = calculate_task_dates(self.tasks_data, project_start_date)
            else:
                self.tasks = []
            
            self.draw_gantt_chart()
            self._draw_dependency_arrows()
            self.canvas.draw()

        except Exception as e:
            tk.messagebox.showerror("Error", f"Could not update chart: {e}")

    def draw_gantt_chart(self):
        self.ax.clear()
        self.chart_items = [] # Reset for redraw

        if not self.tasks:
            self.ax.text(0.5, 0.5, "No tasks to display.\nUse the File menu to start.", 
                         horizontalalignment='center', verticalalignment='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        min_date = min([t['start'] for t in self.tasks if 'start' in t], default=datetime.now())
        max_date = max([t['end'] for t in self.tasks if 'end' in t], default=datetime.now())

        # --- Set View Mode ---
        project_duration_days = (max_date - min_date).days
        if project_duration_days > 270: # Approx 9 months
            self.view_mode = 'monthly'
        elif project_duration_days > 21:
            self.view_mode = 'weekly'
        else:
            self.view_mode = 'daily'

        # --- Setup Universal Coordinate System (based on work days) ---
        self.work_days = []
        end_boundary = max_date + timedelta(days=4)
        
        # Adjust chart start date based on view mode for better margins
        if self.view_mode == 'daily':
            # For daily view, start just one day before the first task
            start_of_chart = min_date - timedelta(days=1)
        else:
            # For weekly/monthly, align to the start of the week
            start_of_chart = min_date - timedelta(days=min_date.weekday())

        temp_date = start_of_chart
        while temp_date < end_boundary:
            if temp_date.weekday() < 5:
                self.work_days.append(temp_date)
            temp_date += timedelta(days=1)
        
        if not self.work_days:
            self.ax.text(0.5, 0.5, "No work days to display in the selected date range.", 
                         horizontalalignment='center', verticalalignment='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return
            
        date_to_index = {date.date(): i for i, date in enumerate(self.work_days)}

        # --- Universal Mapping Functions ---
        def date_to_coord(d):
            return date_to_index.get(d.date())

        def duration_to_width(start_date, end_date):
            start_idx = date_to_index.get(start_date.date())
            end_idx = date_to_index.get(end_date.date())
            if start_idx is None or end_idx is None: return 0
            # +1 because the end day is inclusive
            return end_idx - start_idx + 1

        def subtask_duration_to_width(d):
            return d # Duration is already in work days, which matches our coordinate system

        # --- Common Rendering Logic ---
        if self.show_stages_var.get():
            items_to_render = []
            for task in self.tasks:
                items_to_render.append({'level': 0, 'data': task})
                # Add sub-tasks with their cumulative duration for precise positioning
                cumulative_duration = 0.0
                for sub_task in task.get('sub_tasks', []):
                    items_to_render.append({
                        'level': 1, 
                        'data': sub_task, 
                        'parent_task': task, 
                        'cumulative_duration': cumulative_duration
                    })
                    cumulative_duration += sub_task.get('duration', 0)
            
            y_labels, y_ticks = [], []
            current_y, parent_y = 0, 0

            for item in items_to_render:
                task_data = item['data']
                level = item['level']
                if 'start' not in task_data: continue
                
                if level == 0:
                    start_coord = date_to_coord(task_data['start'])
                else: # level 1
                    parent_task = item['parent_task']
                    # Start coord is parent's start + cumulative duration of prior stages
                    parent_start_coord = date_to_coord(parent_task['start'])
                    if parent_start_coord is None: continue
                    
                    # Calculate the offset from the parent's start coordinate. The cumulative
                    # duration is already in workdays, which matches our coordinate system.
                    offset = subtask_duration_to_width(item['cumulative_duration'])
                    start_coord = parent_start_coord + offset

                if start_coord is None: continue

                if level == 0:
                    parent_y = current_y
                    
                    if self.show_stages_var.get() and task_data.get('sub_tasks'):
                        # In stages view, the container's width must be the precise sum of its
                        # children's durations to prevent rounding errors from breaking the visual.
                        width = sum(st.get('duration', 0) for st in task_data.get('sub_tasks', []))
                    else:
                        # In status view, or for tasks without stages, the width is based on dates.
                        width = duration_to_width(task_data['start'], task_data['end'])

                    patch = self.ax.barh(y=current_y, width=width, left=start_coord, height=0.6, 
                                 color='#e0e0e0', align='center', edgecolor='black')[0]
                    item['patch'] = patch
                    self.chart_items.append(item)
                    y_labels.append(task_data["name"])
                    y_ticks.append(current_y)
                elif level == 1:
                    duration = task_data["duration"]
                    width = subtask_duration_to_width(duration)
                    patch = self.ax.barh(y=parent_y, width=width, left=start_coord, height=0.4, 
                                 color=stage_colors.get(task_data["name"], "gray"), 
                                 align='center', edgecolor='black', alpha=0.9)[0]
                    item['patch'] = patch
                    self.chart_items.append(item)
                if level == 0:
                    current_y += 1
            
            self.ax.set_yticks(y_ticks)
            self.ax.set_yticklabels(y_labels)
            legend_elements = [Patch(facecolor=color, edgecolor='black', label=stage)
                               for stage, color in stage_colors.items()]
            self.ax.legend(handles=legend_elements, loc='lower right')
        else: # Status view
            y_labels = [task["name"] for task in self.tasks]
            self.ax.set_yticks(range(len(self.tasks)))
            self.ax.set_yticklabels(y_labels)

            for i, task in enumerate(self.tasks):
                if 'start' not in task: continue
                
                start_coord = date_to_coord(task['start'])
                if start_coord is None: continue

                width = duration_to_width(task['start'], task['end'])
                agg_status = self._get_aggregate_status(task)
                color = status_colors.get(agg_status, "gray")
                
                patch = self.ax.barh(y=i, width=width, left=start_coord, height=0.5, 
                             color=color, align='center', edgecolor='black', alpha=0.8)[0]
                self.chart_items.append({'level': 0, 'data': task, 'patch': patch})

            legend_elements = [Patch(facecolor=color, edgecolor='black', label=status)
                               for status, color in status_colors.items()]
            self.ax.legend(handles=legend_elements, loc='lower right')

        # --- Setup X-Axis based on View Mode ---
        self.ax.invert_yaxis()
        
        ticks, labels = [], []
        if self.view_mode == 'daily':
            ticks = range(len(self.work_days))
            labels = [d.strftime('%d-%b') for d in self.work_days]
        elif self.view_mode == 'weekly':
            temp_date = self.work_days[0]
            while temp_date <= self.work_days[-1]:
                idx = date_to_index.get(temp_date.date())
                if idx is not None:
                    ticks.append(idx)
                    labels.append(temp_date.strftime('%d-%b'))
                temp_date += timedelta(weeks=1)
        elif self.view_mode == 'monthly':
            last_month_year = None
            for i, day in enumerate(self.work_days):
                month_year = (day.month, day.year)
                if month_year != last_month_year:
                    ticks.append(i)
                    labels.append(day.strftime('%b-%y'))
                    last_month_year = month_year

        self.ax.set_xticks(ticks)
        self.ax.set_xticklabels(labels)
        
        # Common X-axis final setup
        self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation=90, ha='center')
        self.ax.set_xlim(-0.5, len(self.work_days) - 0.5)
        self.ax.grid(axis='x', linestyle='--', alpha=0.6)
        self.ax.set_title(self.project_name_var.get())
        self.ax.set_xlabel('Date')
        self.ax.set_ylabel('Tasks')
        self.figure.tight_layout()
        # self.canvas.draw() # Orchestration is now handled by calculate_and_draw

    def _get_aggregate_status(self, task):
        sub_statuses = [s['status'] for s in task.get('sub_tasks', [])]
        if not sub_statuses:
            return "Not Started"

        if all(s == "Completed" for s in sub_statuses):
            return "Completed"
        if all(s == "Not Started" for s in sub_statuses):
            return "Not Started"
        return "In Progress"

    def manage_stages(self):
        global stage_colors
        dialog = ManageStagesDialog(self, "Manage Stages", stage_colors)
        if not dialog.result:
            return

        new_stage_config = dialog.result
        
        original_names = set(stage_colors.keys())
        final_names = set(new_stage_config.keys())
        
        renamed_stages = {}
        for new_name, data in new_stage_config.items():
            original_name = data['original_name']
            if new_name != original_name:
                renamed_stages[original_name] = new_name
                
        deleted_stages = original_names - set(d['original_name'] for d in new_stage_config.values())
        
        # Apply changes to all tasks
        for task in self.tasks_data:
            if not task.get('sub_tasks'): continue
            
            updated_sub_tasks = []
            for sub_task in task['sub_tasks']:
                # Handle deletions
                if sub_task['name'] in deleted_stages:
                    continue
                # Handle renames
                if sub_task['name'] in renamed_stages:
                    sub_task['name'] = renamed_stages[sub_task['name']]
                
                updated_sub_tasks.append(sub_task)
            task['sub_tasks'] = updated_sub_tasks

        # Update the global stage_colors dictionary
        stage_colors = collections.OrderedDict([(name, data['color']) for name, data in new_stage_config.items()])

        # Redraw everything
        self.populate_treeview()
        self.calculate_and_draw()

    def _draw_dependency_arrows(self):
        if not self.show_dependencies_var.get():
            return # Skip drawing if toggled off
            
        # Initialize connections list for each task to store the patch objects
        for item in self.chart_items:
            if item['level'] == 0:
                if 'connections' not in item['data']:
                    item['data']['connections'] = []
                else:
                    item['data']['connections'].clear()

        tasks_by_name = {t['data']['name']: t for t in self.chart_items if t['level'] == 0}
        
        for item in self.chart_items:
            if item['level'] != 0: continue
            
            task_data = item['data']
            dependency_name = task_data.get('depends_on')
            
            if dependency_name and dependency_name in tasks_by_name:
                predecessor_item = tasks_by_name[dependency_name]
                
                start_patch = predecessor_item.get('patch')
                end_patch = item.get('patch')

                if start_patch and end_patch:
                    start_pos = (start_patch.get_x() + start_patch.get_width(), start_patch.get_y() + start_patch.get_height() / 2)
                    end_pos = (end_patch.get_x(), end_patch.get_y() + end_patch.get_height() / 2)

                    # Check if the points are the same to avoid a warning
                    if start_pos == end_pos: continue
                    
                    # Determine curvature direction based on task positions
                    rad = 0.3 if start_pos[0] > end_pos[0] else -0.3

                    con = ConnectionPatch(
                        xyA=end_pos, 
                        xyB=start_pos,
                        coordsA="data", 
                        coordsB="data",
                        axesA=self.ax, 
                        axesB=self.ax,
                        connectionstyle=f"arc3,rad={rad}",
                        arrowstyle="<|-",
                        shrinkA=5,
                        shrinkB=5,
                        ls='--',
                        color='#555555',
                        lw=1.5
                    )
                    self.ax.add_patch(con)
                    # Store reference to the connection patch in both connected tasks
                    predecessor_item['data']['connections'].append(con)
                    item['data']['connections'].append(con)

    def toggle_link_mode(self):
        self._link_mode_enabled = not self._link_mode_enabled
        if self._link_mode_enabled:
            self.link_button.config(style="Accent.TButton")
            self.canvas.get_tk_widget().config(cursor="crosshair")
            self._link_start_item = None
        else:
            self.link_button.config(style="TButton")
            self.canvas.get_tk_widget().config(cursor="")
            self._link_start_item = None


if __name__ == "__main__":
    app = GanttChartApp()
    app.mainloop() 