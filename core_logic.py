"""
Core calculation logic for the Gantt Chart application.

This module handles date arithmetic for work days and task scheduling,
including dependency resolution and date calculations.
"""

from datetime import datetime, timedelta
from typing import Any
import math


# Type aliases for clarity
TaskDict = dict[str, Any]
SubTaskDict = dict[str, Any]


def add_work_days(start_date: datetime, duration_days: float) -> datetime:
    """
    Add a number of work days to a start date, skipping weekends.
    
    Args:
        start_date: The starting date
        duration_days: Number of work days to add (can be fractional)
    
    Returns:
        The end date after adding the specified work days
    
    Example:
        >>> add_work_days(datetime(2025, 1, 20), 3)  # Monday + 3 days
        datetime(2025, 1, 22)  # Wednesday
    """
    days_to_add = math.ceil(duration_days) - 1
    if duration_days > 0 and days_to_add < 0:
        days_to_add = 0
    
    end_date = start_date
    while days_to_add > 0:
        end_date += timedelta(days=1)
        if end_date.weekday() < 5:  # Monday=0, Friday=4
            days_to_add -= 1
    
    return end_date


def count_work_days(start_date: datetime, end_date: datetime) -> int:
    """
    Count the number of work days (Mon-Fri) between two dates, inclusive.
    
    Args:
        start_date: The start of the range
        end_date: The end of the range
    
    Returns:
        Number of work days in the range. Returns 0 if start > end.
    
    Example:
        >>> count_work_days(datetime(2025, 1, 20), datetime(2025, 1, 24))
        5  # Monday through Friday
    """
    if start_date > end_date:
        return 0
    
    work_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:
            work_days += 1
        current_date += timedelta(days=1)
    
    return work_days


def calculate_task_dates(
    tasks_list: list[TaskDict], 
    project_start_date: datetime
) -> list[TaskDict]:
    """
    Calculate start and end dates for all tasks based on dependencies and overrides.
    
    This function mutates the input tasks_list, adding 'start' and 'end' datetime
    fields to each task and sub-task.
    
    Args:
        tasks_list: List of task dictionaries with the following structure:
            - name: str - Task name (required)
            - depends_on: str | None - Name of dependency task
            - start_date_override: str | None - Manual start date (DD-MM-YYYY)
            - end_date_override: str | None - Manual end date (DD-MM-YYYY)
            - sub_tasks: list[SubTaskDict] - List of sub-task/stage dictionaries
        project_start_date: The default start date for tasks without dependencies
    
    Returns:
        The same tasks_list with calculated 'start' and 'end' fields added
    
    Raises:
        ValueError: If there's a circular dependency, missing dependency, 
                   or invalid date format
    """
    # Clear all previously calculated dates to ensure a fresh calculation
    for task in tasks_list:
        if 'start' in task:
            del task['start']
        if 'end' in task:
            del task['end']
        for sub_task in task.get('sub_tasks', []):
            if 'start' in sub_task:
                del sub_task['start']
            if 'end' in sub_task:
                del sub_task['end']

    tasks_by_name: dict[str, TaskDict] = {task["name"]: task for task in tasks_list}
    calculated_tasks: set[str] = set()

    # Iterate multiple times to resolve dependencies in order
    max_iterations = len(tasks_list) * 2
    for _ in range(max_iterations):
        made_progress = False
        
        for task in tasks_list:
            if task["name"] in calculated_tasks:
                continue

            # Determine the start date for this task
            start_date_for_task = _resolve_task_start_date(
                task, tasks_by_name, calculated_tasks, project_start_date
            )

            # If we have a start date, we can calculate this task and its sub-tasks
            if start_date_for_task is not None:
                _calculate_task_and_subtasks(task, start_date_for_task)
                calculated_tasks.add(task["name"])
                made_progress = True

        # Check if all tasks are calculated
        if len(calculated_tasks) == len(tasks_list):
            return tasks_list
        
        # Check for circular dependency or missing task reference
        if not made_progress and len(calculated_tasks) < len(tasks_list):
            uncalculated = [
                t['name'] for t in tasks_list 
                if t['name'] not in calculated_tasks
            ]
            
            # Try to identify the specific issue
            error_details = _diagnose_dependency_issue(tasks_list, tasks_by_name, uncalculated)
            raise ValueError(error_details)
    
    return tasks_list


def _resolve_task_start_date(
    task: TaskDict,
    tasks_by_name: dict[str, TaskDict],
    calculated_tasks: set[str],
    project_start_date: datetime
) -> datetime | None:
    """
    Resolve the start date for a task based on overrides, dependencies, or defaults.
    
    Returns None if the task depends on another task that hasn't been calculated yet.
    """
    override_str = task.get("start_date_override")
    dependency_name = task.get("depends_on")

    # Priority 1: Manual start date override
    if override_str:
        try:
            start_date = datetime.strptime(override_str, "%d-%m-%Y")
            # If the override date falls on a weekend, move it to the next Monday
            while start_date.weekday() >= 5:
                start_date += timedelta(days=1)
            return start_date
        except ValueError:
            raise ValueError(
                f"Invalid date format for '{task['name']}'. Please use DD-MM-YYYY."
            )
    
    # Priority 2: Dependency-based start (day after dependency ends)
    if dependency_name:
        if dependency_name in calculated_tasks:
            dependency = tasks_by_name[dependency_name]
            next_day = dependency["end"] + timedelta(days=1)
            # Skip weekends
            while next_day.weekday() >= 5:
                next_day += timedelta(days=1)
            return next_day
        else:
            # Dependency not yet calculated, skip this task for now
            return None
    
    # Priority 3: Default to project start date
    return project_start_date


def _calculate_task_and_subtasks(
    task: TaskDict, 
    start_date_for_task: datetime
) -> None:
    """
    Calculate dates for a task and all its sub-tasks.
    
    This function mutates the task dictionary in place.
    """
    # Check for a task-level end date override
    end_date_override: datetime | None = None
    end_date_override_str = task.get("end_date_override")
    if end_date_override_str:
        try:
            parsed_date = datetime.strptime(end_date_override_str, "%d-%m-%Y")
            if parsed_date >= start_date_for_task:
                end_date_override = parsed_date
        except ValueError:
            pass  # Invalid format, ignore override

    # Calculate sub-task dates
    cumulative_duration_days: float = 0
    sub_tasks = task.get("sub_tasks", [])
    
    for i, sub_task in enumerate(sub_tasks):
        current_duration = sub_task['duration']
        
        # First sub-task starts at task start; others continue from cumulative duration
        if i == 0:
            sub_task["start"] = start_date_for_task
        else:
            sub_task["start"] = add_work_days(start_date_for_task, cumulative_duration_days)
        
        sub_task["end"] = add_work_days(sub_task["start"], current_duration)
        cumulative_duration_days += current_duration

    # Set the parent task's start and end
    if sub_tasks:
        task["start"] = sub_tasks[0]["start"]
        if end_date_override:
            # Use override for the parent task's visual container
            task["end"] = end_date_override
        else:
            # Calculate end based on the sum of stage durations
            total_duration = sum(st.get('duration', 0) for st in sub_tasks)
            task["end"] = add_work_days(task["start"], total_duration)
    else:
        # Task with no sub-tasks
        task["start"] = start_date_for_task
        task["end"] = add_work_days(start_date_for_task, 0)


def _diagnose_dependency_issue(
    tasks_list: list[TaskDict],
    tasks_by_name: dict[str, TaskDict],
    uncalculated: list[str]
) -> str:
    """
    Diagnose why tasks couldn't be calculated and return a user-friendly error message.
    """
    # Check for missing dependencies first
    for task_name in uncalculated:
        task = tasks_by_name.get(task_name)
        if not task:
            continue
        dep_name = task.get('depends_on')
        if dep_name and dep_name not in tasks_by_name:
            return (
                f"Task '{task_name}' depends on '{dep_name}', "
                f"but no task with that name exists.\n\n"
                f"Please remove or correct this dependency."
            )
    
    # Try to find a cycle
    cycle = _find_dependency_cycle(tasks_list, tasks_by_name)
    if cycle:
        cycle_str = " → ".join(cycle)
        return (
            f"Circular dependency detected:\n\n"
            f"  {cycle_str}\n\n"
            f"Each task in this chain depends on the next, creating a loop.\n"
            f"Remove one of these dependencies to fix the issue."
        )
    
    # Generic fallback
    return (
        f"Unable to calculate dates for: {', '.join(uncalculated)}\n\n"
        f"This may be due to missing or invalid dependencies."
    )


def _find_dependency_cycle(
    tasks_list: list[TaskDict],
    tasks_by_name: dict[str, TaskDict]
) -> list[str] | None:
    """
    Find a dependency cycle if one exists.
    
    Returns:
        List of task names forming the cycle, or None if no cycle exists.
    """
    # Track visited and currently-in-stack nodes for DFS
    visited = set()
    in_stack = set()
    parent = {}  # Track path for cycle reconstruction
    
    def dfs(task_name: str) -> list[str] | None:
        if task_name in in_stack:
            # Found a cycle - reconstruct it
            cycle = [task_name]
            current = parent.get(task_name)
            while current and current != task_name:
                cycle.append(current)
                current = parent.get(current)
            cycle.append(task_name)
            cycle.reverse()
            return cycle
        
        if task_name in visited:
            return None
        
        visited.add(task_name)
        in_stack.add(task_name)
        
        task = tasks_by_name.get(task_name)
        if task:
            dep_name = task.get('depends_on')
            if dep_name and dep_name in tasks_by_name:
                parent[dep_name] = task_name
                result = dfs(dep_name)
                if result:
                    return result
        
        in_stack.remove(task_name)
        return None
    
    # Run DFS from each task
    for task in tasks_list:
        result = dfs(task['name'])
        if result:
            return result
    
    return None


def would_create_cycle(
    tasks_list: list[TaskDict],
    task_name: str,
    proposed_dependency: str
) -> bool:
    """
    Check if setting task_name to depend on proposed_dependency would create a cycle.
    
    Args:
        tasks_list: The current list of tasks
        task_name: The task that would gain a new dependency
        proposed_dependency: The task that would become the dependency
    
    Returns:
        True if setting this dependency would create a cycle, False otherwise.
    """
    if not proposed_dependency or proposed_dependency == "None":
        return False
    
    if task_name == proposed_dependency:
        return True  # Can't depend on yourself
    
    # Build a temporary dependency graph with the proposed change
    tasks_by_name = {t['name']: t for t in tasks_list}
    
    # Check if proposed_dependency transitively depends on task_name
    visited = set()
    current = proposed_dependency
    
    while current:
        if current == task_name:
            return True  # Found a cycle
        if current in visited:
            break  # Already checked this path
        visited.add(current)
        
        task = tasks_by_name.get(current)
        if task:
            current = task.get('depends_on')
        else:
            break
    
    return False


def get_dependency_chain(tasks_list: list[TaskDict], task_name: str) -> list[str]:
    """
    Get the chain of tasks that a given task depends on.
    
    Returns:
        List of task names in dependency order (immediate dependency first).
    """
    tasks_by_name = {t['name']: t for t in tasks_list}
    chain = []
    visited = set()
    current = task_name
    
    while current:
        task = tasks_by_name.get(current)
        if not task:
            break
        
        dep_name = task.get('depends_on')
        if dep_name:
            if dep_name in visited:
                chain.append(f"{dep_name} (cycle!)")
                break
            chain.append(dep_name)
            visited.add(dep_name)
            current = dep_name
        else:
            break
    
    return chain
