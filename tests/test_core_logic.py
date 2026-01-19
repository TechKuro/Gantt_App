"""
Unit tests for the core_logic module.

Tests cover:
- add_work_days: Adding work days while skipping weekends
- count_work_days: Counting work days between dates
- calculate_task_dates: Dependency resolution and date calculation
"""

import pytest
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_logic import add_work_days, count_work_days, calculate_task_dates


class TestAddWorkDays:
    """Tests for the add_work_days function."""

    def test_add_zero_days(self):
        """Adding 0 days returns the same date."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 0)
        assert result == monday

    def test_add_one_day_from_monday(self):
        """Adding 1 day from Monday returns Monday (same day)."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 1)
        assert result == monday

    def test_add_two_days_from_monday(self):
        """Adding 2 days from Monday returns Tuesday."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 2)
        assert result == datetime(2025, 1, 21)  # Tuesday

    def test_add_five_days_from_monday(self):
        """Adding 5 days from Monday returns Friday (same week)."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 5)
        assert result == datetime(2025, 1, 24)  # Friday

    def test_add_six_days_skips_weekend(self):
        """Adding 6 days from Monday skips weekend to next Monday."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 6)
        assert result == datetime(2025, 1, 27)  # Next Monday

    def test_add_ten_days_spans_two_weeks(self):
        """Adding 10 days spans two full work weeks."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 10)
        assert result == datetime(2025, 1, 31)  # Friday of second week

    def test_add_days_from_friday(self):
        """Adding days from Friday correctly skips weekend."""
        friday = datetime(2025, 1, 24)  # Friday
        result = add_work_days(friday, 2)
        assert result == datetime(2025, 1, 27)  # Monday

    def test_fractional_days_rounds_up(self):
        """Fractional days are rounded up for calendar calculation."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 1.5)
        # ceil(1.5) - 1 = 1, so adds 1 work day
        assert result == datetime(2025, 1, 21)  # Tuesday

    def test_small_fractional_days(self):
        """Very small fractions still work correctly."""
        monday = datetime(2025, 1, 20)  # Monday
        result = add_work_days(monday, 0.25)
        assert result == monday  # Same day


class TestCountWorkDays:
    """Tests for the count_work_days function."""

    def test_same_day_weekday(self):
        """Same day on a weekday counts as 1."""
        monday = datetime(2025, 1, 20)  # Monday
        result = count_work_days(monday, monday)
        assert result == 1

    def test_same_day_weekend(self):
        """Same day on a weekend counts as 0."""
        saturday = datetime(2025, 1, 25)  # Saturday
        result = count_work_days(saturday, saturday)
        assert result == 0

    def test_monday_to_friday(self):
        """Monday through Friday is 5 work days."""
        monday = datetime(2025, 1, 20)
        friday = datetime(2025, 1, 24)
        result = count_work_days(monday, friday)
        assert result == 5

    def test_full_week_including_weekend(self):
        """A full week (Mon-Sun) still counts as 5 work days."""
        monday = datetime(2025, 1, 20)
        sunday = datetime(2025, 1, 26)
        result = count_work_days(monday, sunday)
        assert result == 5

    def test_two_weeks(self):
        """Two full work weeks is 10 work days."""
        monday = datetime(2025, 1, 20)
        friday = datetime(2025, 1, 31)
        result = count_work_days(monday, friday)
        assert result == 10

    def test_end_before_start_returns_zero(self):
        """If end date is before start date, return 0."""
        monday = datetime(2025, 1, 20)
        friday = datetime(2025, 1, 17)
        result = count_work_days(monday, friday)
        assert result == 0

    def test_weekend_only(self):
        """Saturday to Sunday is 0 work days."""
        saturday = datetime(2025, 1, 25)
        sunday = datetime(2025, 1, 26)
        result = count_work_days(saturday, sunday)
        assert result == 0


class TestCalculateTaskDates:
    """Tests for the calculate_task_dates function."""

    def test_single_task_no_dependency(self):
        """A single task with no dependency starts at project start."""
        project_start = datetime(2025, 1, 20)  # Monday
        tasks = [{
            "name": "Task 1",
            "depends_on": None,
            "sub_tasks": [
                {"name": "Stage 1", "duration": 3, "status": "Not Started"}
            ]
        }]
        
        result = calculate_task_dates(tasks, project_start)
        
        assert result[0]["start"] == project_start
        assert result[0]["sub_tasks"][0]["start"] == project_start
        assert result[0]["sub_tasks"][0]["end"] == datetime(2025, 1, 22)  # Wednesday

    def test_task_with_start_date_override(self):
        """A task with a start date override uses that date."""
        project_start = datetime(2025, 1, 20)  # Monday
        tasks = [{
            "name": "Task 1",
            "depends_on": None,
            "start_date_override": "27-01-2025",  # Next Monday
            "sub_tasks": [
                {"name": "Stage 1", "duration": 1, "status": "Not Started"}
            ]
        }]
        
        result = calculate_task_dates(tasks, project_start)
        
        assert result[0]["start"] == datetime(2025, 1, 27)

    def test_weekend_override_moves_to_monday(self):
        """A start date override on Saturday moves to Monday."""
        project_start = datetime(2025, 1, 20)
        tasks = [{
            "name": "Task 1",
            "depends_on": None,
            "start_date_override": "25-01-2025",  # Saturday
            "sub_tasks": [
                {"name": "Stage 1", "duration": 1, "status": "Not Started"}
            ]
        }]
        
        result = calculate_task_dates(tasks, project_start)
        
        assert result[0]["start"] == datetime(2025, 1, 27)  # Monday

    def test_simple_dependency_chain(self):
        """Task B starts after Task A ends."""
        project_start = datetime(2025, 1, 20)  # Monday
        tasks = [
            {
                "name": "Task A",
                "depends_on": None,
                "sub_tasks": [
                    {"name": "Stage 1", "duration": 3, "status": "Not Started"}
                ]
            },
            {
                "name": "Task B",
                "depends_on": "Task A",
                "sub_tasks": [
                    {"name": "Stage 1", "duration": 2, "status": "Not Started"}
                ]
            }
        ]
        
        result = calculate_task_dates(tasks, project_start)
        
        # Task A: Mon 20 - Wed 22
        assert result[0]["start"] == datetime(2025, 1, 20)
        assert result[0]["end"] == datetime(2025, 1, 22)
        
        # Task B: Thu 23 - Fri 24
        assert result[1]["start"] == datetime(2025, 1, 23)
        assert result[1]["end"] == datetime(2025, 1, 24)

    def test_dependency_skips_weekend(self):
        """Dependency ending Friday causes next task to start Monday."""
        project_start = datetime(2025, 1, 20)  # Monday
        tasks = [
            {
                "name": "Task A",
                "depends_on": None,
                "sub_tasks": [
                    {"name": "Stage 1", "duration": 5, "status": "Not Started"}
                ]
            },
            {
                "name": "Task B",
                "depends_on": "Task A",
                "sub_tasks": [
                    {"name": "Stage 1", "duration": 1, "status": "Not Started"}
                ]
            }
        ]
        
        result = calculate_task_dates(tasks, project_start)
        
        # Task A: Mon 20 - Fri 24
        assert result[0]["end"] == datetime(2025, 1, 24)
        
        # Task B: Mon 27 (skips weekend)
        assert result[1]["start"] == datetime(2025, 1, 27)

    def test_multiple_sub_tasks(self):
        """Multiple sub-tasks are scheduled sequentially."""
        project_start = datetime(2025, 1, 20)  # Monday
        tasks = [{
            "name": "Task 1",
            "depends_on": None,
            "sub_tasks": [
                {"name": "Preparation", "duration": 2, "status": "Not Started"},
                {"name": "Implementation", "duration": 3, "status": "Not Started"},
                {"name": "Training", "duration": 1, "status": "Not Started"}
            ]
        }]
        
        result = calculate_task_dates(tasks, project_start)
        
        # Preparation: Mon 20 - Tue 21 (2 days: day 1 = Mon, day 2 = Tue)
        assert result[0]["sub_tasks"][0]["start"] == datetime(2025, 1, 20)
        assert result[0]["sub_tasks"][0]["end"] == datetime(2025, 1, 21)
        
        # Implementation starts where Preparation left off (cumulative duration = 2)
        # add_work_days(Mon 20, 2) = Tue 21, so Implementation starts Tue 21
        # Implementation: Tue 21 - Thu 23 (3 days: Tue, Wed, Thu)
        assert result[0]["sub_tasks"][1]["start"] == datetime(2025, 1, 21)
        assert result[0]["sub_tasks"][1]["end"] == datetime(2025, 1, 23)
        
        # Training starts at cumulative duration = 5
        # add_work_days(Mon 20, 5) = Fri 24
        # Training: Fri 24 (1 day)
        assert result[0]["sub_tasks"][2]["start"] == datetime(2025, 1, 24)
        assert result[0]["sub_tasks"][2]["end"] == datetime(2025, 1, 24)

    def test_end_date_override(self):
        """Task end date override sets the parent task end."""
        project_start = datetime(2025, 1, 20)
        tasks = [{
            "name": "Task 1",
            "depends_on": None,
            "end_date_override": "31-01-2025",
            "sub_tasks": [
                {"name": "Stage 1", "duration": 2, "status": "Not Started"}
            ]
        }]
        
        result = calculate_task_dates(tasks, project_start)
        
        # Sub-task ends normally, but parent uses override
        assert result[0]["sub_tasks"][0]["end"] == datetime(2025, 1, 21)
        assert result[0]["end"] == datetime(2025, 1, 31)

    def test_task_with_no_subtasks(self):
        """Task with no sub-tasks gets zero duration."""
        project_start = datetime(2025, 1, 20)
        tasks = [{
            "name": "Milestone",
            "depends_on": None,
            "sub_tasks": []
        }]
        
        result = calculate_task_dates(tasks, project_start)
        
        assert result[0]["start"] == project_start
        assert result[0]["end"] == project_start

    def test_circular_dependency_raises_error(self):
        """Circular dependencies raise ValueError."""
        project_start = datetime(2025, 1, 20)
        tasks = [
            {
                "name": "Task A",
                "depends_on": "Task B",
                "sub_tasks": [{"name": "S", "duration": 1, "status": "Not Started"}]
            },
            {
                "name": "Task B",
                "depends_on": "Task A",
                "sub_tasks": [{"name": "S", "duration": 1, "status": "Not Started"}]
            }
        ]
        
        with pytest.raises(ValueError) as exc_info:
            calculate_task_dates(tasks, project_start)
        
        assert "Circular dependency" in str(exc_info.value)

    def test_missing_dependency_raises_error(self):
        """Referencing a non-existent task raises ValueError."""
        project_start = datetime(2025, 1, 20)
        tasks = [{
            "name": "Task A",
            "depends_on": "Non-existent Task",
            "sub_tasks": [{"name": "S", "duration": 1, "status": "Not Started"}]
        }]
        
        with pytest.raises(ValueError) as exc_info:
            calculate_task_dates(tasks, project_start)
        
        assert "Task A" in str(exc_info.value)

    def test_invalid_date_format_raises_error(self):
        """Invalid date format in override raises ValueError."""
        project_start = datetime(2025, 1, 20)
        tasks = [{
            "name": "Task A",
            "depends_on": None,
            "start_date_override": "2025-01-20",  # Wrong format (should be DD-MM-YYYY)
            "sub_tasks": [{"name": "S", "duration": 1, "status": "Not Started"}]
        }]
        
        with pytest.raises(ValueError) as exc_info:
            calculate_task_dates(tasks, project_start)
        
        assert "Invalid date format" in str(exc_info.value)

    def test_out_of_order_dependencies_resolved(self):
        """Tasks can be defined in any order; dependencies are resolved correctly."""
        project_start = datetime(2025, 1, 20)
        tasks = [
            {
                "name": "Task C",
                "depends_on": "Task B",
                "sub_tasks": [{"name": "S", "duration": 1, "status": "Not Started"}]
            },
            {
                "name": "Task A",
                "depends_on": None,
                "sub_tasks": [{"name": "S", "duration": 2, "status": "Not Started"}]
            },
            {
                "name": "Task B",
                "depends_on": "Task A",
                "sub_tasks": [{"name": "S", "duration": 1, "status": "Not Started"}]
            }
        ]
        
        result = calculate_task_dates(tasks, project_start)
        
        # Find tasks by name
        task_a = next(t for t in result if t["name"] == "Task A")
        task_b = next(t for t in result if t["name"] == "Task B")
        task_c = next(t for t in result if t["name"] == "Task C")
        
        # Task A starts first
        assert task_a["start"] == datetime(2025, 1, 20)
        # Task B follows A
        assert task_b["start"] == datetime(2025, 1, 22)
        # Task C follows B
        assert task_c["start"] == datetime(2025, 1, 23)

    def test_clears_previous_calculations(self):
        """Running calculation twice clears old start/end fields."""
        project_start = datetime(2025, 1, 20)
        tasks = [{
            "name": "Task 1",
            "depends_on": None,
            "sub_tasks": [{"name": "S", "duration": 1, "status": "Not Started"}]
        }]
        
        # First calculation
        calculate_task_dates(tasks, project_start)
        old_start = tasks[0]["start"]
        
        # Second calculation with different project start
        new_start = datetime(2025, 2, 3)
        calculate_task_dates(tasks, new_start)
        
        assert tasks[0]["start"] == new_start
        assert tasks[0]["start"] != old_start
