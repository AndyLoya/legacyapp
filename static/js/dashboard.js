/* Dashboard - Task Manager */

let selectedTaskId = null;
let selectedProjectId = null;

function selectTask(id) {
  selectedTaskId = id;
  fetch(API_TASK(id))
    .then((r) => r.json())
    .then((task) => {
      document.getElementById("task_title").value = task.title || "";
      document.getElementById("task_description").value = task.description || "";
      document.getElementById("task_status").value = task.status || "Pending";
      document.getElementById("task_priority").value = task.priority || "Medium";
      document.getElementById("task_project_id").value = task.project_id || "";
      document.getElementById("task_assigned_to").value = task.assigned_to || "";
      document.getElementById("task_due_date").value = task.due_date || "";
      document.getElementById("task_hours").value = task.estimated_hours || "";
      document.querySelectorAll(".task-row").forEach((r) => r.classList.remove("selected"));
      const row = document.querySelector(`.task-row[data-task-id="${id}"]`);
      if (row) row.classList.add("selected");
    })
    .catch(() => alert("Error loading task"));
}

function submitTaskUpdate() {
  if (!selectedTaskId) {
    alert("Select a task from the table");
    return;
  }
  const form = document.getElementById("taskForm");
  form.action = TASK_UPDATE_URL(selectedTaskId);
  form.submit();
}

function submitTaskDelete() {
  if (!selectedTaskId) {
    alert("Select a task");
    return;
  }
  if (!confirm("Delete this task?")) return;
  const form = document.getElementById("taskDeleteForm");
  form.action = TASK_DELETE_URL(selectedTaskId);
  form.submit();
}

function clearTaskForm() {
  selectedTaskId = null;
  document.getElementById("task_title").value = "";
  document.getElementById("task_description").value = "";
  document.getElementById("task_status").value = "Pending";
  document.getElementById("task_priority").value = "Medium";
  document.getElementById("task_project_id").value = "";
  document.getElementById("task_assigned_to").value = "";
  document.getElementById("task_due_date").value = "";
  document.getElementById("task_hours").value = "";
  document.querySelectorAll(".task-row").forEach((r) => r.classList.remove("selected"));
  const form = document.getElementById("taskForm");
  if (form) form.action = form.getAttribute("data-add-action") || "";
}

(function () {
  const taskForm = document.getElementById("taskForm");
  if (taskForm) taskForm.setAttribute("data-add-action", taskForm.action);
})();

function selectProjectRow(row) {
  selectedProjectId = row.dataset.projectId || null;
  document.getElementById("project_name").value = row.dataset.projectName || "";
  document.getElementById("project_description").value = row.dataset.projectDescription || "";
  document.querySelectorAll(".project-row").forEach((r) => r.classList.remove("selected"));
  row.classList.add("selected");
}

function selectProject(id, name, description) {
  selectedProjectId = id;
  document.getElementById("project_name").value = name || "";
  document.getElementById("project_description").value = description || "";
}

function submitProjectUpdate() {
  if (!selectedProjectId) {
    alert("Select a project from the table");
    return;
  }
  const form = document.getElementById("projectForm");
  form.action = PROJECT_UPDATE_URL(selectedProjectId);
  form.submit();
}

function submitProjectDelete() {
  if (!selectedProjectId) {
    alert("Select a project");
    return;
  }
  if (!confirm("Delete this project?")) return;
  const form = document.getElementById("projectDeleteForm");
  form.action = PROJECT_DELETE_URL(selectedProjectId);
  form.submit();
}

function loadComments() {
  const taskId = document.getElementById("comment_task_id").value.trim();
  const area = document.getElementById("commentsArea");
  if (!taskId) {
    area.textContent = "Enter a task ID and click Load Comments.";
    return;
  }
  fetch(API_COMMENTS(taskId))
    .then((r) => r.json())
    .then((comments) => {
      if (comments.length === 0) {
        area.textContent = "No comments for this task.";
        return;
      }
      area.textContent = comments
        .map(
          (c) =>
            `[${c.created_at}] ${c.user}: ${c.text}`
        )
        .join("\n---\n");
    })
    .catch(() => (area.textContent = "Error loading comments."));
}

function loadHistory() {
  const taskId = document.getElementById("history_task_id").value.trim();
  const area = document.getElementById("historyArea");
  const url = taskId ? API_HISTORY_TASK(taskId) : API_HISTORY;
  fetch(url)
    .then((r) => r.json())
    .then((entries) => {
      if (entries.length === 0) {
        area.textContent = "No history.";
        return;
      }
      area.textContent = entries
        .map(
          (e) =>
            `Task #${e.task_id} - ${e.action} - ${e.timestamp}\n  User: ${e.user}\n  Before: ${e.old_value}\n  After: ${e.new_value}`
        )
        .join("\n---\n");
    })
    .catch(() => (area.textContent = "Error loading history."));
}

function loadAllHistory() {
  document.getElementById("history_task_id").value = "";
  loadHistory();
}

function loadNotifications() {
  const area = document.getElementById("notificationsArea");
  fetch(API_NOTIFICATIONS)
    .then((r) => r.json())
    .then((list) => {
      if (list.length === 0) {
        area.textContent = "No new notifications.";
        return;
      }
      area.textContent = list
        .map((n) => `• [${n.type}] ${n.message} (${n.created_at})`)
        .join("\n");
    })
    .catch(() => (area.textContent = "Error loading notifications."));
}

function searchTasks() {
  const q = document.getElementById("search_text").value;
  const status = document.getElementById("search_status").value;
  const priority = document.getElementById("search_priority").value;
  const projectId = document.getElementById("search_project_id").value || "0";
  const params = new URLSearchParams({ q, status, priority, project_id: projectId });
  const tbody = document.getElementById("searchTableBody");
  fetch(`${API_SEARCH}?${params}`)
    .then((r) => r.json())
    .then((tasks) => {
      tbody.innerHTML = tasks
        .map(
          (t) =>
            `<tr>
              <td>${t.id}</td>
              <td>${t.title}</td>
              <td>${t.status}</td>
              <td>${t.priority}</td>
              <td>${t.project}</td>
            </tr>`
        )
        .join("");
      if (tasks.length === 0) tbody.innerHTML = "<tr><td colspan='5'>No results</td></tr>";
    })
    .catch(() => (tbody.innerHTML = "<tr><td colspan='5'>Search error</td></tr>"));
}

function generateReport(type) {
  const area = document.getElementById("reportsArea");
  fetch(API_REPORT(type))
    .then((r) => r.json())
    .then((data) => {
      area.textContent = `=== REPORT: ${type.toUpperCase()} ===\n\n` + (data.lines || []).join("\n");
    })
    .catch(() => (area.textContent = "Error generating report."));
}
