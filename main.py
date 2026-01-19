import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import math
import json
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Patch, ConnectionPatch
import copy
import collections

# Local imports
from config import default_tasks_data, status_colors, stage_colors as default_stage_colors
from core_logic import calculate_task_dates, add_work_days
from dialogs import EditTaskDialog, ManageStagesDialog


class GanttChartApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gantt Chart Planner")
        self.geometry("1800x800")
        
        # --- App State & Configuration ---
        self.tasks_data = []
        self.status_colors = status_colors
        self.stage_colors = copy.deepcopy(default_stage_colors)

        # --- UI State ---
        self._is_updating = False
        self.controls_visible = True
        self._drag_data = None
        self._legend_drag_data = None  # For legend dragging
        self.current_legend = None     # Reference to current legend object
        self.saved_legend_position = None  # Store legend position across redraws
        self._is_redrawing_chart = False  # Flag to prevent position tracking during redraws
        self.project_name_var = tk.StringVar(value="New Project")
        self.show_stages_var = tk.BooleanVar(value=True)
        self.show_dependencies_var = tk.BooleanVar(value=True)
        self.chart_items = []
        self._tree_drag_data = {}
        self.style = ttk.Style()
        self.style.configure('Accent.TButton', relief=tk.SUNKEN)
        self._highlighted_patches = {} # For hover effects
        self.current_filepath = None
        self.view_mode = 'daily'
        self.task_rows = {} 

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
        
        # --- Initialization ---
        self.setup_chart_canvas()
        self.build_controls()
        self.new_blank_project() # Start with a blank project
        self.connect_drag_events()
        self.canvas.mpl_connect('button_release_event', self._on_legend_drag_release)

    def connect_drag_events(self):
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)

    def on_press(self, event):
        # Let matplotlib's event handling take over if the click is on the legend.
        # We check this first to ensure our custom task-dragging logic doesn't interfere.
        # The `draggable=True` flag on the legend object handles the dragging automatically.
        if self.current_legend and self.current_legend.get_window_extent().contains(event.x, event.y):
            return

        if event.inaxes != self.ax: return

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
        # Check if we're hovering over the legend for visual feedback
        if self.current_legend and event.inaxes == self.ax:
            try:
                legend_bbox = self.current_legend.get_window_extent(self.canvas.get_renderer())
                if legend_bbox.contains(event.x, event.y):
                    # Change cursor to indicate legend is draggable
                    self.canvas.get_tk_widget().config(cursor="hand2")
                elif self._drag_data is None:
                    # Reset cursor if not dragging anything
                    self.canvas.get_tk_widget().config(cursor="")
            except Exception:
                # If there's any error getting legend bounds, just continue
                pass

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
                    # Resize the specific sub-task (stage), capping it if the parent has a fixed end date.
                    parent_task = item.get('parent_task')
                    end_override_str = parent_task.get('end_date_override') if parent_task else None

                    if parent_task and end_override_str and parent_task.get('start'):
                        try:
                            end_date_override = datetime.strptime(end_override_str, "%d-%m-%Y")
                            total_allowed = count_work_days(parent_task['start'], end_date_override)
                            
                            sum_of_others = 0
                            for sub_task in parent_task.get('sub_tasks', []):
                                if sub_task is not task_data:
                                    sum_of_others += sub_task.get('duration', 0)

                            max_allowed_for_current = total_allowed - sum_of_others
                            if max_allowed_for_current < 0.25: max_allowed_for_current = 0.25
                            
                            if new_duration > max_allowed_for_current:
                                new_duration = round(max_allowed_for_current, 2)

                        except (ValueError):
                             pass # On error, proceed with uncapped duration.
                    
                    task_data['duration'] = new_duration
                else:
                    # Resize the parent task by adjusting its last sub-task
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
        if self._drag_data is not None:
            self._drag_data = None
            
        # Reset cursor unless we're over the legend
        cursor_to_set = ""
        if self.current_legend and event and event.inaxes == self.ax:
            try:
                legend_bbox = self.current_legend.get_window_extent(self.canvas.get_renderer())
                if legend_bbox.contains(event.x, event.y):
                    cursor_to_set = "hand2"
            except Exception:
                pass
                
        self.canvas.get_tk_widget().config(cursor=cursor_to_set)

    def reset_legend_position(self):
        """Reset the legend to its default position (lower right)."""
        # Clear the saved position so it uses the default
        self.saved_legend_position = None
        
        # Redraw the chart. The draw_gantt_chart method will handle recreating
        # the legend in the default location.
        self.calculate_and_draw()

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
        file_menu.add_command(label="Reset Legend Position", command=self.reset_legend_position)
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
        self.saved_legend_position = None  # Reset legend position for new project
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
        
        # Load tasks from the template
        self.tasks_data = copy.deepcopy(template_data["tasks"])
        
        # Load stages from the template, updating the instance's definition
        if "stages" in template_data:
            if isinstance(template_data["stages"], dict): # old format
                self.stage_colors = collections.OrderedDict(template_data["stages"].items())
            else: # new format: list of [key, value]
                self.stage_colors = collections.OrderedDict(template_data["stages"])

        # Set a default start date for the new project
        self.project_start_date_var.set(datetime.now().strftime("%d-%m-%Y"))
        
        self.project_name_var.set("New Project from Template")
        self.current_filepath = None
        self.saved_legend_position = None  # Reset legend position for template-based project
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
            
        if "stages" in project_data:
            if isinstance(project_data["stages"], dict): # old format for backward compatibility
                self.stage_colors = collections.OrderedDict(project_data["stages"].items())
            else: # new format: list of [key, value]
                self.stage_colors = collections.OrderedDict(project_data["stages"])

        self.current_filepath = filepath
        self.project_name_var.set(project_data.get("project_name", "Untitled Project"))
        self.project_start_date_var.set(project_data["project_start_date"])
        self.tasks_data = project_data["tasks"]
        
        # Restore legend position if saved
        self.saved_legend_position = project_data.get("legend_position")
        
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
            
        tasks_to_save = copy.deepcopy(self.tasks_data)
        for task in tasks_to_save:
            task.pop('start', None)
            task.pop('end', None)
            task.pop('connections', None)
            for sub_task in task.get('sub_tasks', []):
                sub_task.pop('start', None)
                sub_task.pop('end', None)

        project_data = {
            "project_name": self.project_name_var.get(),
            "project_start_date": self.project_start_date_var.get(),
            "tasks": tasks_to_save,
            "stages": list(self.stage_colors.items()),
            "legend_position": self.saved_legend_position
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
                        "status": "Not Started"
                    }
                    clean_task["sub_tasks"].append(clean_sub_task)
            template_tasks.append(clean_task)

        template_data = {
            "tasks": template_tasks,
            "stages": list(self.stage_colors.items())
        }

        with open(filepath, 'w') as f:
            json.dump(template_data, f, indent=4)
        
        messagebox.showinfo("Template Saved", f"Template successfully saved to\n{filepath}")

    def export_chart(self):
        # Check tasks_data (the source of truth) not self.tasks (calculated result)
        if not self.tasks_data:
            messagebox.showinfo("Export Chart", "There is nothing to export.")
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
            self.figure.savefig(filepath, bbox_inches='tight', dpi=300)
            messagebox.showinfo("Export Successful", f"Chart successfully saved to\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred while exporting the chart: {e}")

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

    def populate_treeview(self):
        for i in self.task_tree.get_children():
            self.task_tree.delete(i)
        
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

    def on_tree_double_click(self, event):
        self._tree_drag_data = {} 
        
        column = self.task_tree.identify_column(event.x)
        if column == "#0": 
            iid = self.task_tree.identify_row(event.y)
            if iid and not self.task_tree.parent(iid): 
                self._edit_task_name_inline(iid)
        else:
            iid = self.task_tree.identify_row(event.y)
            if iid:
                self.edit_task(item_id=iid)

    def _edit_task_name_inline(self, iid):
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
                for task in self.tasks_data:
                    if task['name'] == original_name:
                        task['name'] = new_name
                        break
                
                for task in self.tasks_data:
                    if task.get('depends_on') == original_name:
                        task['depends_on'] = new_name
                
                self.populate_treeview()
                self.calculate_and_draw()

        entry.bind("<Return>", on_commit)
        entry.bind("<FocusOut>", on_commit)

    def on_tree_press(self, event):
        iid = self.task_tree.identify_row(event.y)
        if not iid: return

        parent_iid = self.task_tree.parent(iid)
        if not parent_iid:
            # Store initial position for drag detection
            self._tree_drag_data = {
                "type": "task", 
                "iid": iid, 
                "start_x": event.x, 
                "start_y": event.y,
                "has_moved": False
            }

    def on_tree_motion(self, event):
        if not self._tree_drag_data: return

        # Check if we've moved enough to consider this a drag operation
        start_x = self._tree_drag_data["start_x"]
        start_y = self._tree_drag_data["start_y"]
        
        # Require at least 5 pixels of movement to start dragging
        if abs(event.x - start_x) < 5 and abs(event.y - start_y) < 5:
            return
        
        # Mark that we've actually moved (started dragging)
        self._tree_drag_data["has_moved"] = True

        drag_iid = self._tree_drag_data["iid"]
        target_iid = self.task_tree.identify_row(event.y)
        if not target_iid or target_iid == drag_iid: return

        if not self.task_tree.parent(target_iid): 
            target_index = self.task_tree.index(target_iid)
            self.task_tree.move(drag_iid, "", target_index)

    def on_tree_release(self, event):
        if not self._tree_drag_data:
            return

        # Only process reordering if we actually moved (dragged)
        if self._tree_drag_data.get("has_moved", False):
            # Check if the order actually changed before triggering a refresh
            new_task_order_iids = self.task_tree.get_children("")
            new_task_names = [self.task_tree.item(iid, "text") for iid in new_task_order_iids]
            
            # Get the current order of task names
            current_task_names = [task['name'] for task in self.tasks_data]
            
            # Only update if the order actually changed
            if new_task_names != current_task_names:
                tasks_dict = {task['name']: task for task in self.tasks_data}
                
                new_tasks_data_list = []
                for name in new_task_names:
                    if name in tasks_dict:
                        new_tasks_data_list.append(tasks_dict[name])
                
                self.tasks_data = new_tasks_data_list
                self.on_ui_change()
        else:
            # This was just a click, not a drag - allow normal selection
            iid = self._tree_drag_data.get("iid")
            if iid:
                # Ensure the item is selected (normal treeview behavior)
                self.task_tree.selection_set(iid)
                self.task_tree.focus(iid)
        
        self._tree_drag_data = {}

    def edit_task(self, item_id=None):
        selected_id = None
        if item_id:
            selected_id = item_id
        else:
            selected_item = self.task_tree.selection()
            if not selected_item:
                messagebox.showwarning("Edit Task", "Please select a task to edit.")
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
            
            dialog = EditTaskDialog(self, "Edit Task", task_to_edit, calculated_task_data, other_task_names, self.project_start_date_var.get(), self.status_colors, self.stage_colors)
            
            if dialog.result:
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
        existing_stage_names = self.stage_colors.keys()
        new_task['sub_tasks'] = [st for st in new_task['sub_tasks'] if st['name'] in existing_stage_names]

        self.tasks_data.append(new_task)
        self.populate_treeview()
        self.calculate_and_draw()

    def remove_task(self):
        selected_item = self.task_tree.selection()
        if not selected_item:
            messagebox.showwarning("Remove Task", "Please select a task to remove.")
            return

        selected_id = selected_item[0]
        
        parent_iid = self.task_tree.parent(selected_id)
        if parent_iid: 
            selected_id = parent_iid

        task_name_to_remove = self.task_tree.item(selected_id, "text")
        task_to_remove = None
        for task in self.tasks_data:
            if task['name'] == task_name_to_remove:
                task_to_remove = task
                break
        
        if task_to_remove:
            for other_task in self.tasks_data:
                if other_task.get('depends_on') == task_name_to_remove:
                    other_task['depends_on'] = None

            self.tasks_data.remove(task_to_remove)
            self.populate_treeview()
            self.calculate_and_draw()
        
    def calculate_and_draw(self):
        try:
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
            messagebox.showerror("Error", f"Could not update chart: {e}")

    def draw_gantt_chart(self):
        self.ax.clear()
        self.chart_items = []
        self.current_legend = None  # Clear previous legend reference

        if not self.tasks:
            self.ax.text(0.5, 0.5, "No tasks to display.\nUse the File menu to start.", 
                         horizontalalignment='center', verticalalignment='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        # --- Date Range Calculation ---
        all_dates = [t['start'] for t in self.tasks if 'start' in t] + \
                    [t['end'] for t in self.tasks if 'end' in t]

        # Also consider pinned start dates from both calculated tasks AND raw task data
        for t in self.tasks:
            override_str = t.get('start_date_override')
            if override_str:
                try:
                    all_dates.append(datetime.strptime(override_str, "%d-%m-%Y"))
                except ValueError:
                    pass # Ignore invalid format

        # IMPORTANT: Also check raw tasks_data for start date overrides
        for t in self.tasks_data:
            override_str = t.get('start_date_override')
            if override_str:
                try:
                    override_date = datetime.strptime(override_str, "%d-%m-%Y")
                    all_dates.append(override_date)
                except ValueError:
                    pass # Ignore invalid format

        # Ensure the project start date from the UI is included
        try:
            proj_start = datetime.strptime(self.project_start_date_var.get(), "%d-%m-%Y")
            all_dates.append(proj_start)
        except ValueError:
            pass # Ignore invalid format on project start

        if not all_dates:
            min_date = datetime.now()
            max_date = datetime.now() + timedelta(days=30)
        else:
            min_date = min(all_dates)
            max_date = max(all_dates)

        project_duration_days = (max_date - min_date).days
        if project_duration_days > 365 * 2: # ~2 years
            self.view_mode = 'yearly'
        elif project_duration_days > 90: # ~3 months
            self.view_mode = 'monthly'
        elif project_duration_days > 21:
            self.view_mode = 'weekly'
        else:
            self.view_mode = 'daily'

        # --- Work Day Calculation ---
        self.work_days = []
        # Add a buffer for visualization
        start_of_chart = min_date - timedelta(days=min_date.weekday() + 1) 
        end_boundary = max_date + timedelta(days=7)
        
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

        def date_to_coord(d):
            return date_to_index.get(d.date())

        def duration_to_width(start_date, end_date):
            start_idx = date_to_index.get(start_date.date())
            end_idx = date_to_index.get(end_date.date())
            
            # If start date is not a work day, return 0 (task shouldn't be displayed)
            if start_idx is None: 
                return 0
            
            # If end date is not a work day (e.g., weekend), find the previous work day
            if end_idx is None:
                # Move end_date backwards to find the last work day before or on the end date
                temp_end = end_date
                while temp_end >= start_date and end_idx is None:
                    end_idx = date_to_index.get(temp_end.date())
                    if end_idx is None:
                        temp_end -= timedelta(days=1)
                
                # If we still can't find a work day, the task duration might be invalid
                if end_idx is None:
                    return 0
            
            # Ensure we have a positive width
            width = max(1, end_idx - start_idx + 1)
            return width

        def subtask_duration_to_width(d):
            return d

        if self.show_stages_var.get():
            items_to_render = []
            for task in self.tasks:
                items_to_render.append({'level': 0, 'data': task})
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
                else: 
                    parent_task = item['parent_task']
                    parent_start_coord = date_to_coord(parent_task['start'])
                    if parent_start_coord is None: continue
                    
                    offset = subtask_duration_to_width(item['cumulative_duration'])
                    start_coord = parent_start_coord + offset

                if start_coord is None: continue

                if level == 0:
                    parent_y = current_y
                    
                    if self.show_stages_var.get() and task_data.get('sub_tasks'):
                        width = sum(st.get('duration', 0) for st in task_data.get('sub_tasks', []))
                    else:
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
                                 color=self.stage_colors.get(task_data["name"], "gray"), 
                                 align='center', edgecolor='black', alpha=0.9)[0]
                    item['patch'] = patch
                    self.chart_items.append(item)
                if level == 0:
                    current_y += 1
            
            self.ax.set_yticks(y_ticks)
            self.ax.set_yticklabels(y_labels)
            legend_elements = [Patch(facecolor=color, edgecolor='black', label=stage)
                               for stage, color in self.stage_colors.items()]
            
            # Create legend with saved position or default
            if self.saved_legend_position:
                # When using bbox_to_anchor with figure coordinates, we must also set the transform.
                self.current_legend = self.ax.legend(handles=legend_elements,
                                                   loc="lower left", # Place the legend's lower-left corner at the anchor
                                                   bbox_to_anchor=self.saved_legend_position,
                                                   bbox_transform=self.figure.transFigure, # Use figure-level coordinates
                                                   draggable=True)
            else:
                self.current_legend = self.ax.legend(handles=legend_elements, loc='lower right', draggable=True)
            
        else: # Status view
            y_labels = [task["name"] for task in self.tasks]
            self.ax.set_yticks(range(len(self.tasks)))
            self.ax.set_yticklabels(y_labels)

            for i, task in enumerate(self.tasks):
                if 'start' not in task: continue
                
                start_coord = date_to_coord(task['start'])
                if start_coord is None: continue

                width = duration_to_width(task['start'], task['end'])
                if width <= 0: continue
                
                agg_status = self._get_aggregate_status(task)
                color = self.status_colors.get(agg_status, "gray")
                
                patch = self.ax.barh(y=i, width=width, left=start_coord, height=0.5, 
                             color=color, align='center', edgecolor='black', alpha=0.8)[0]
                self.chart_items.append({'level': 0, 'data': task, 'patch': patch})

            legend_elements = [Patch(facecolor=color, edgecolor='black', label=status)
                               for status, color in self.status_colors.items()]
            
            # Create legend with saved position or default
            if self.saved_legend_position:
                # When using bbox_to_anchor with figure coordinates, we must also set the transform.
                self.current_legend = self.ax.legend(handles=legend_elements,
                                                   loc="lower left", # Place the legend's lower-left corner at the anchor
                                                   bbox_to_anchor=self.saved_legend_position,
                                                   bbox_transform=self.figure.transFigure, # Use figure-level coordinates
                                                   draggable=True)
            else:
                self.current_legend = self.ax.legend(handles=legend_elements, loc='lower right', draggable=True)
            
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
        elif self.view_mode == 'yearly':
            # For yearly view, show months with year context, but avoid overcrowding
            last_year = None
            last_month_year = None
            month_count = 0
            
            for i, day in enumerate(self.work_days):
                year = day.year
                month_year = (day.month, day.year)
                
                # Add month markers, but include year for January or when year changes
                if month_year != last_month_year:
                    month_count += 1
                    # Always show January with year, or show every other month if too many
                    show_label = (day.month == 1 or year != last_year or 
                                 (month_count % 2 == 1 and len(self.work_days) < 1500) or  # Show more labels for shorter ranges
                                 (month_count % 3 == 1 and len(self.work_days) >= 1500))   # Show fewer labels for very long ranges
                    
                    if show_label:
                        ticks.append(i)
                        if day.month == 1 or year != last_year:
                            # Show month with year for context
                            labels.append(f"{day.strftime('%b')} {year}")
                            last_year = year
                        else:
                            # Show just month abbreviation
                            labels.append(day.strftime('%b'))
                    last_month_year = month_year

        self.ax.set_xticks(ticks)
        self.ax.set_xticklabels(labels)
        
        self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation=90, ha='center')
        self.ax.set_xlim(-0.5, len(self.work_days) - 0.5)
        self.ax.grid(axis='x', linestyle='--', alpha=0.6)
        self.ax.set_title(self.project_name_var.get())
        self.ax.set_xlabel('Date')
        self.ax.set_ylabel('Tasks')
        self.figure.tight_layout()

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
        dialog = ManageStagesDialog(self, "Manage Stages", self.stage_colors)
        if not dialog.result:
            return

        new_stage_config = dialog.result
        
        original_names = set(self.stage_colors.keys())
        final_names = set(new_stage_config.keys())
        
        renamed_stages = {}
        for new_name, data in new_stage_config.items():
            original_name = data['original_name']
            if new_name != original_name:
                renamed_stages[original_name] = new_name
                
        deleted_stages = original_names - set(d['original_name'] for d in new_stage_config.values())
        
        for task in self.tasks_data:
            if not task.get('sub_tasks'): continue
            
            updated_sub_tasks = []
            for sub_task in task['sub_tasks']:
                if sub_task['name'] in deleted_stages:
                    continue
                if sub_task['name'] in renamed_stages:
                    sub_task['name'] = renamed_stages[sub_task['name']]
                
                updated_sub_tasks.append(sub_task)
            task['sub_tasks'] = updated_sub_tasks

        self.stage_colors = collections.OrderedDict([(name, data['color']) for name, data in new_stage_config.items()])

        self.populate_treeview()
        self.calculate_and_draw()

    def _draw_dependency_arrows(self):
        if not self.show_dependencies_var.get():
            return
            
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

                    if start_pos == end_pos: continue
                    
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
                    predecessor_item['data']['connections'].append(con)
                    item['data']['connections'].append(con)



    def _on_legend_drag_release(self, event):
        """Saves the legend's position only when a drag operation on it is completed."""
        # Check if the legend exists. We don't check if the event is inside the axes
        # anymore, allowing the position to be saved anywhere on the figure.
        if self.current_legend:
            try:
                # Check if the mouse release happened over the legend's final position
                if self.current_legend.get_window_extent().contains(event.x, event.y):
                    # We transform the legend's bounding box from display (pixel)
                    # coordinates to the FIGURE's relative coordinates (0-1).
                    inv = self.figure.transFigure.inverted()
                    bbox_fig = inv.transform_bbox(self.current_legend.get_window_extent())
                    # We save the full bounding box (x, y, width, height) in figure coordinates.
                    self.saved_legend_position = (bbox_fig.x0, bbox_fig.y0, bbox_fig.width, bbox_fig.height)
            except Exception:
                # Silently ignore any errors during this check
                pass


if __name__ == "__main__":
    app = GanttChartApp()
    app.mainloop() 