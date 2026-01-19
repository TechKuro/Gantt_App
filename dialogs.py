import tkinter as tk
from tkinter import ttk, simpledialog
import copy
import collections
from datetime import datetime

from core_logic import add_work_days, count_work_days

class EditTaskDialog(simpledialog.Dialog):
    def __init__(self, parent, title, task_data, calculated_task_data, all_task_names, project_start_date, status_colors, stage_colors):
        self.task_data_original = task_data
        self.task_data_copy = copy.deepcopy(task_data)
        self.calculated_task_data = calculated_task_data
        self.all_task_names = all_task_names
        self.project_start_date = project_start_date
        self.status_colors = status_colors
        self.stage_colors = stage_colors
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
        status_options = list(self.status_colors.keys())

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
        available_stages = [name for name in self.stage_colors.keys() if name not in current_stage_names]
        
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
        """
        When a duration is changed, if the parent task has a fixed end date,
        this change is capped to prevent the total duration from exceeding the limit.
        """
        end_override_str = self.end_date_override_var.get()
        if end_override_str:
            try:
                task_start_date = self._get_task_start_date()
                end_date_override = datetime.strptime(end_override_str, "%d-%m-%Y")
                total_allowed = count_work_days(task_start_date, end_date_override)

                sum_of_others = 0
                for i, var_set in enumerate(self.sub_task_vars):
                    if i != index:
                        sum_of_others += var_set['duration_var'].get()
                
                max_allowed_for_current = total_allowed - sum_of_others
                if max_allowed_for_current < 0.25: max_allowed_for_current = 0.25

                current_var = self.sub_task_vars[index]['duration_var']
                if current_var.get() > max_allowed_for_current:
                    current_var.set(round(max_allowed_for_current, 2))

            except (tk.TclError, ValueError):
                pass # Ignore errors, just proceed to update display

        self._update_stage_display()

    def _on_end_date_change(self, index):
        """
        Calculates a new duration based on the entered end date, then caps
        that duration if it violates the parent task's fixed end date.
        """
        try:
            sub_task_vars = self.sub_task_vars[index]
            end_date = datetime.strptime(sub_task_vars['end_date_var'].get(), "%d-%m-%Y")
            
            task_start_date = self._get_task_start_date()
            predecessor_duration = 0
            for i in range(index):
                predecessor_duration += self.sub_task_vars[i]['duration_var'].get()
            
            start_date = add_work_days(task_start_date, predecessor_duration)

            if end_date < start_date:
                self._update_stage_display()
                return

            duration = count_work_days(start_date, end_date)
            sub_task_vars['duration_var'].set(float(duration))

        except (ValueError, tk.TclError):
            pass # Error will be handled by the subsequent call
        
        # Now that duration is updated, run the capping logic and refresh the view.
        self._on_duration_change(index)

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


class ColumnMappingDialog(simpledialog.Dialog):
    """
    Dialog for mapping CSV/Excel columns to Gantt task fields during import.
    """
    def __init__(self, parent, title, columns):
        self.columns = columns
        self.mapping = {}
        super().__init__(parent, title)

    def body(self, master):
        instruction_frame = ttk.Frame(master, padding=10)
        instruction_frame.pack(fill=tk.X)
        
        ttk.Label(
            instruction_frame, 
            text="Map the columns from your file to the corresponding Gantt fields.\n"
                 "Leave fields as 'Not Mapped' if not applicable.",
            justify=tk.LEFT
        ).pack(anchor="w")

        mapping_frame = ttk.LabelFrame(master, text="Column Mapping", padding=10)
        mapping_frame.pack(fill=tk.X, padx=10, pady=10)

        # Define the fields we want to map
        self.field_definitions = [
            ("Task Name", True),      # (field_name, required)
            ("Start Date", False),
            ("End Date", False),
            ("Stage", False),
            ("Status", False),
            ("Dependencies", False),
        ]

        self.mapping_vars = {}
        column_options = ["Not Mapped"] + self.columns

        for i, (field_name, required) in enumerate(self.field_definitions):
            label_text = f"{field_name}:"
            if required:
                label_text = f"{field_name}*:"
            
            ttk.Label(mapping_frame, text=label_text).grid(
                row=i, column=0, sticky="w", padx=5, pady=3
            )
            
            var = tk.StringVar(value="Not Mapped")
            
            # Try to auto-detect matching columns
            for col in self.columns:
                col_lower = col.lower().replace("_", " ").replace("-", " ")
                field_lower = field_name.lower()
                if field_lower in col_lower or col_lower in field_lower:
                    var.set(col)
                    break
            
            combo = ttk.Combobox(
                mapping_frame, 
                textvariable=var, 
                values=column_options, 
                state="readonly", 
                width=30
            )
            combo.grid(row=i, column=1, sticky="w", padx=5, pady=3)
            
            self.mapping_vars[field_name] = var

        # Required field note
        ttk.Label(
            master, 
            text="* Required field",
            font=("Arial", 8, "italic")
        ).pack(anchor="w", padx=10, pady=(0, 10))

        return mapping_frame

    def validate(self):
        """Validate that required fields are mapped."""
        task_name_mapping = self.mapping_vars.get("Task Name")
        if not task_name_mapping or task_name_mapping.get() == "Not Mapped":
            from tkinter import messagebox
            messagebox.showerror(
                "Mapping Required", 
                "You must map a column to 'Task Name'.",
                parent=self
            )
            return False
        return True

    def apply(self):
        """Build the mapping dictionary from the selected values."""
        for field_name, var in self.mapping_vars.items():
            value = var.get()
            if value and value != "Not Mapped":
                self.mapping[field_name] = value