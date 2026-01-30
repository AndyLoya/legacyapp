"""MongoDB collections used by Task Manager (see db.py for connection).

Collections:
  - users:     { _id, username, password }
  - projects:  { _id, name, description }
  - tasks:    { _id, title, description, status, priority, project_id, assigned_to,
                due_date, estimated_hours, actual_hours, created_by, created_at, updated_at }
  - comments: { _id, task_id, user_id, comment_text, created_at }
  - history:  { _id, task_id, user_id, action, old_value, new_value, timestamp }
  - notifications: { _id, user_id, message, type, read, created_at }

All _id and foreign key fields (project_id, assigned_to, created_by, user_id, task_id)
are MongoDB ObjectId. Use MONGODB_URI in the environment to set the connection string.
"""
