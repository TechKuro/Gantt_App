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