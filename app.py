"""Task Manager - Flask application (MongoDB)."""
import os
import csv
import io
from datetime import datetime, date, time
from functools import wraps

from bson import ObjectId
from pymongo.errors import ServerSelectionTimeoutError
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    session,
)

from db import get_db, init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")


# Max lengths for text fields (must match frontend maxlength)
MAX_TITLE = 100
MAX_DESCRIPTION = 5000
MAX_PROJECT_NAME = 80
MAX_PROJECT_DESCRIPTION = 2000
MAX_COMMENT = 3000
MAX_SEARCH = 200
MAX_HOURS = 999
MIN_HOURS = 0
OBJECTID_HEX_LEN = 24


def _oid(s):
    """Convert string to ObjectId; return None if invalid."""
    if not s:
        return None
    s = s.strip()
    if len(s) != OBJECTID_HEX_LEN or not all(c in "0123456789abcdefABCDEF" for c in s):
        return None
    try:
        return ObjectId(s)
    except Exception:
        return None


def _validate_length(s, max_len, field_name):
    """Return (True, s) if len(s) <= max_len, else (False, error_message)."""
    if s is None:
        s = ""
    s = s.strip() if isinstance(s, str) else str(s)
    if len(s) > max_len:
        return False, f"{field_name} must be at most {max_len} characters (got {len(s)})."
    return True, s


def _date_for_mongo(d):
    """Convert date to datetime for BSON (MongoDB does not support date type)."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d
    return datetime.combine(d, time(0, 0, 0))


def get_current_user():
    """Current user from session (MongoDB user doc with 'username' and '_id')."""
    if "user_id" not in session:
        return None
    uid = _oid(session["user_id"])
    if not uid:
        return None
    return get_db().users.find_one({"_id": uid})


def login_required(f):
    """Decorator: require logged-in user."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if get_current_user() is None:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_current_user():
    """Inject current_user into all templates."""
    return {"current_user": get_current_user()}


def seed_collections():
    """Create collections and seed initial data if empty."""
    db = get_db()
    if db.users.count_documents({}) == 0:
        for u in [("admin", "admin"), ("user1", "user1"), ("user2", "user2")]:
            db.users.insert_one({"username": u[0], "password": u[1]})
    if db.projects.count_documents({}) == 0:
        for p in [
            ("Demo Project", "Sample project"),
            ("Alpha Project", "Main project"),
            ("Beta Project", "Secondary project"),
        ]:
            db.projects.insert_one({"name": p[0], "description": p[1]})


# ---------- Auth routes ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().users.find_one({"username": username, "password": password})
        if user:
            session["user_id"] = str(user["_id"])
            flash("Signed in successfully.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("user_id", None)
    flash("Signed out.", "info")
    return redirect(url_for("login"))


# ---------- Dashboard ----------

@app.route("/")
def index():
    if get_current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    tab = request.args.get("tab", "tasks")
    db = get_db()
    projects_cursor = db.projects.find().sort("name", 1)
    projects = [_doc_with_id(p) for p in projects_cursor]
    users_cursor = db.users.find().sort("username", 1)
    users = [_doc_with_id(u) for u in users_cursor]
    tasks = _get_tasks_for_dashboard(db.tasks.find())
    stats = _compute_stats(tasks)
    return render_template(
        "dashboard.html",
        tab=tab,
        projects=projects,
        users=users,
        tasks=tasks,
        stats=stats,
    )


def _doc_with_id(doc):
    """Add string 'id' to a MongoDB doc for templates."""
    if doc is None:
        return None
    d = dict(doc)
    d["id"] = str(d["_id"])
    return d


def _get_tasks_for_dashboard(cursor):
    """Convert task cursor to list of dicts with id, project_name, assignee_username."""
    db = get_db()
    tasks = list(cursor)
    projects_by_id = {str(p["_id"]): p for p in db.projects.find()}
    users_by_id = {str(u["_id"]): u for u in db.users.find()}
    out = []
    for t in tasks:
        tid = str(t["_id"])
        pid = str(t["project_id"]) if t.get("project_id") else None
        aid = str(t["assigned_to"]) if t.get("assigned_to") else None
        dd = t.get("due_date")
        if dd:
            due_str = dd.strftime("%Y-%m-%d") if hasattr(dd, "strftime") else str(dd)[:10]
        else:
            due_str = None
        out.append({
            "id": tid,
            "title": t.get("title", ""),
            "status": t.get("status", "Pending"),
            "priority": t.get("priority", "Medium"),
            "project_name": projects_by_id.get(pid, {}).get("name") if pid else None,
            "assignee_username": users_by_id.get(aid, {}).get("username") if aid else None,
            "due_date": dd,
            "due_date_str": due_str,
        })
    return out


def _compute_stats(tasks):
    total = len(tasks)
    completed = sum(1 for t in tasks if t.get("status") == "Completed")
    pending = total - completed
    high_priority = sum(1 for t in tasks if t.get("priority") in ("High", "Critical"))
    overdue = 0
    today = date.today()
    for t in tasks:
        dd = t.get("due_date")
        if dd and t.get("status") != "Completed":
            if isinstance(dd, datetime):
                d = dd.date()
            elif isinstance(dd, date):
                d = dd
            else:
                try:
                    d = dd.date() if hasattr(dd, "date") else datetime.fromisoformat(str(dd).replace("Z", "+00:00")).date()
                except Exception:
                    continue
            if d < today:
                overdue += 1
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "high_priority": high_priority,
        "overdue": overdue,
    }


# ---------- Tasks ----------

@app.route("/task/add", methods=["POST"])
@login_required
def task_add():
    title_raw = request.form.get("task_title", "").strip()
    ok, title = _validate_length(title_raw, MAX_TITLE, "Title")
    if not ok:
        flash(title, "error")
        return redirect(url_for("dashboard", tab="tasks"))
    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    desc_raw = request.form.get("task_description", "")
    ok, description = _validate_length(desc_raw, MAX_DESCRIPTION, "Description")
    if not ok:
        flash(description, "error")
        return redirect(url_for("dashboard", tab="tasks"))
    try:
        hours_val = float(request.form.get("task_hours") or 0)
        if not (MIN_HOURS <= hours_val <= MAX_HOURS):
            flash(f"Estimated hours must be between {MIN_HOURS} and {MAX_HOURS}.", "error")
            return redirect(url_for("dashboard", tab="tasks"))
    except (TypeError, ValueError):
        flash("Estimated hours must be a number between 0 and 999.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    try:
        due = request.form.get("task_due_date")
        due_date = datetime.strptime(due, "%Y-%m-%d").date() if due else None
    except ValueError:
        due_date = None
    raw_project = request.form.get("task_project_id") or ""
    raw_assigned = request.form.get("task_assigned_to") or ""
    project_id = _oid(raw_project)
    assigned_to = _oid(raw_assigned)
    user = get_current_user()
    now = datetime.utcnow()
    task_doc = {
        "title": title,
        "description": description,
        "status": request.form.get("task_status", "Pending"),
        "priority": request.form.get("task_priority", "Medium"),
        "project_id": project_id,
        "assigned_to": assigned_to,
        "due_date": _date_for_mongo(due_date),
        "estimated_hours": hours_val,
        "actual_hours": 0,
        "created_by": user["_id"],
        "created_at": now,
        "updated_at": now,
    }
    r = get_db().tasks.insert_one(task_doc)
    task_id = r.inserted_id
    _add_history(task_id, "CREATED", "", title)
    if assigned_to:
        _add_notification(assigned_to, f"New task assigned: {title}", "task_assigned")
    flash("Task created.", "success")
    return redirect(url_for("dashboard", tab="tasks"))


@app.route("/task/update/<task_id>", methods=["POST"])
@login_required
def task_update(task_id):
    oid = _oid(task_id)
    if not oid:
        flash("Invalid task.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    task = get_db().tasks.find_one({"_id": oid})
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    title_raw = request.form.get("task_title", "").strip()
    ok, title = _validate_length(title_raw, MAX_TITLE, "Title")
    if not ok:
        flash(title, "error")
        return redirect(url_for("dashboard", tab="tasks"))
    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    desc_raw = request.form.get("task_description", "")
    ok, description = _validate_length(desc_raw, MAX_DESCRIPTION, "Description")
    if not ok:
        flash(description, "error")
        return redirect(url_for("dashboard", tab="tasks"))
    try:
        hours_val = float(request.form.get("task_hours") or 0)
        if not (MIN_HOURS <= hours_val <= MAX_HOURS):
            flash(f"Estimated hours must be between {MIN_HOURS} and {MAX_HOURS}.", "error")
            return redirect(url_for("dashboard", tab="tasks"))
    except (TypeError, ValueError):
        flash("Estimated hours must be a number between 0 and 999.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    try:
        due = request.form.get("task_due_date")
        due_date = datetime.strptime(due, "%Y-%m-%d").date() if due else None
    except ValueError:
        due_date = task.get("due_date")
        if isinstance(due_date, datetime):
            due_date = due_date.date()
    raw_project = request.form.get("task_project_id") or ""
    raw_assigned = request.form.get("task_assigned_to") or ""
    project_id = _oid(raw_project)
    assigned_to = _oid(raw_assigned)
    old_status = task.get("status")
    old_title = task.get("title")
    get_db().tasks.update_one(
        {"_id": oid},
        {
            "$set": {
                "title": title,
                "description": description,
                "status": request.form.get("task_status", "Pending"),
                "priority": request.form.get("task_priority", "Medium"),
                "project_id": project_id,
                "assigned_to": assigned_to,
                "due_date": _date_for_mongo(due_date),
                "estimated_hours": hours_val,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    if old_status != request.form.get("task_status"):
        _add_history(oid, "STATUS_CHANGED", old_status or "", request.form.get("task_status", ""))
    if old_title != title:
        _add_history(oid, "TITLE_CHANGED", old_title or "", title)
    if assigned_to:
        _add_notification(assigned_to, f"Task updated: {title}", "task_updated")
    flash("Task updated.", "success")
    return redirect(url_for("dashboard", tab="tasks"))


@app.route("/task/delete/<task_id>", methods=["POST"])
@login_required
def task_delete(task_id):
    oid = _oid(task_id)
    if not oid:
        flash("Invalid task.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    task = get_db().tasks.find_one({"_id": oid})
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    title = task.get("title", "")
    _add_history(oid, "DELETED", title, "")
    get_db().tasks.delete_one({"_id": oid})
    flash("Task deleted.", "success")
    return redirect(url_for("dashboard", tab="tasks"))


# ---------- Projects ----------

@app.route("/project/add", methods=["POST"])
@login_required
def project_add():
    name_raw = request.form.get("project_name", "").strip()
    ok, name = _validate_length(name_raw, MAX_PROJECT_NAME, "Project name")
    if not ok:
        flash(name, "error")
        return redirect(url_for("dashboard", tab="projects"))
    if not name:
        flash("Project name is required.", "error")
        return redirect(url_for("dashboard", tab="projects"))
    desc_raw = request.form.get("project_description", "")
    ok, description = _validate_length(desc_raw, MAX_PROJECT_DESCRIPTION, "Project description")
    if not ok:
        flash(description, "error")
        return redirect(url_for("dashboard", tab="projects"))
    get_db().projects.insert_one({
        "name": name,
        "description": description,
    })
    flash("Project created.", "success")
    return redirect(url_for("dashboard", tab="projects"))


@app.route("/project/update/<project_id>", methods=["POST"])
@login_required
def project_update(project_id):
    oid = _oid(project_id)
    if not oid:
        flash("Invalid project.", "error")
        return redirect(url_for("dashboard", tab="projects"))
    project = get_db().projects.find_one({"_id": oid})
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for("dashboard", tab="projects"))
    name_raw = request.form.get("project_name", "").strip()
    ok, name = _validate_length(name_raw, MAX_PROJECT_NAME, "Project name")
    if not ok:
        flash(name, "error")
        return redirect(url_for("dashboard", tab="projects"))
    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("dashboard", tab="projects"))
    desc_raw = request.form.get("project_description", "")
    ok, description = _validate_length(desc_raw, MAX_PROJECT_DESCRIPTION, "Project description")
    if not ok:
        flash(description, "error")
        return redirect(url_for("dashboard", tab="projects"))
    get_db().projects.update_one(
        {"_id": oid},
        {"$set": {"name": name, "description": description}},
    )
    flash("Project updated.", "success")
    return redirect(url_for("dashboard", tab="projects"))


@app.route("/project/delete/<project_id>", methods=["POST"])
@login_required
def project_delete(project_id):
    oid = _oid(project_id)
    if not oid:
        flash("Invalid project.", "error")
        return redirect(url_for("dashboard", tab="projects"))
    get_db().projects.delete_one({"_id": oid})
    flash("Project deleted.", "success")
    return redirect(url_for("dashboard", tab="projects"))


# ---------- Comments ----------

@app.route("/comment/add", methods=["POST"])
@login_required
def comment_add():
    try:
        task_id = request.form.get("comment_task_id", "").strip()
        oid = _oid(task_id)
    except Exception:
        oid = None
    if not oid:
        flash("Invalid task ID (must be 24 hex characters).", "error")
        return redirect(url_for("dashboard", tab="comments"))
    text_raw = request.form.get("comment_text", "").strip()
    ok, text = _validate_length(text_raw, MAX_COMMENT, "Comment text")
    if not ok:
        flash(text, "error")
        return redirect(url_for("dashboard", tab="comments"))
    if not text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("dashboard", tab="comments"))
    if not get_db().tasks.find_one({"_id": oid}):
        flash("Task not found.", "error")
        return redirect(url_for("dashboard", tab="comments"))
    get_db().comments.insert_one({
        "task_id": oid,
        "user_id": get_current_user()["_id"],
        "comment_text": text,
        "created_at": datetime.utcnow(),
    })
    flash("Comment added.", "success")
    return redirect(url_for("dashboard", tab="comments"))


# ---------- Notifications ----------

@app.route("/notifications/read", methods=["POST"])
@login_required
def notifications_mark_read():
    get_db().notifications.update_many(
        {"user_id": get_current_user()["_id"]},
        {"$set": {"read": True}},
    )
    flash("Notifications marked as read.", "success")
    return redirect(url_for("dashboard", tab="notifications"))


# ---------- API ----------

@app.route("/api/task/<task_id>")
@login_required
def api_task(task_id):
    oid = _oid(task_id)
    if not oid:
        return jsonify({"error": "Invalid task"}), 404
    task = get_db().tasks.find_one({"_id": oid})
    if not task:
        return jsonify({"error": "Not found"}), 404
    dd = task.get("due_date")
    due_str = ""
    if dd:
        due_str = dd.isoformat() if isinstance(dd, date) else str(dd)[:10]
    return jsonify({
        "id": str(task["_id"]),
        "title": task.get("title", ""),
        "description": task.get("description", ""),
        "status": task.get("status", "Pending"),
        "priority": task.get("priority", "Medium"),
        "project_id": str(task["project_id"]) if task.get("project_id") else "",
        "assigned_to": str(task["assigned_to"]) if task.get("assigned_to") else "",
        "due_date": due_str,
        "estimated_hours": task.get("estimated_hours", 0),
    })


@app.route("/api/comments/<task_id>")
@login_required
def api_comments(task_id):
    oid = _oid(task_id)
    if not oid:
        return jsonify([])
    comments = list(get_db().comments.find({"task_id": oid}).sort("created_at", 1))
    users = {u["_id"]: u["username"] for u in get_db().users.find()}
    return jsonify([
        {
            "id": str(c["_id"]),
            "user": users.get(c["user_id"], "?"),
            "text": c.get("comment_text", ""),
            "created_at": c.get("created_at", datetime.utcnow()).isoformat(),
        }
        for c in comments
    ])


@app.route("/api/history")
@app.route("/api/history/<task_id>")
@login_required
def api_history(task_id=None):
    q = {}
    if task_id:
        oid = _oid(task_id)
        if oid:
            q["task_id"] = oid
    entries = list(get_db().history.find(q).sort("timestamp", -1).limit(100))
    users = {u["_id"]: u["username"] for u in get_db().users.find()}
    return jsonify([
        {
            "id": str(e["_id"]),
            "task_id": str(e["task_id"]),
            "user": users.get(e["user_id"], "?"),
            "action": e.get("action", ""),
            "old_value": e.get("old_value", ""),
            "new_value": e.get("new_value", ""),
            "timestamp": e.get("timestamp", datetime.utcnow()).isoformat(),
        }
        for e in entries
    ])


@app.route("/api/notifications")
@login_required
def api_notifications():
    notifs = list(
        get_db().notifications.find({
            "user_id": get_current_user()["_id"],
            "read": False,
        }).sort("created_at", -1)
    )
    return jsonify([
        {
            "id": str(n["_id"]),
            "message": n.get("message", ""),
            "type": n.get("type", "info"),
            "created_at": n.get("created_at", datetime.utcnow()).isoformat(),
        }
        for n in notifs
    ])


@app.route("/api/search")
@login_required
def api_search():
    q_filter = {}
    q_raw = request.args.get("q", "").strip().lower()
    ok, q = _validate_length(q_raw, MAX_SEARCH, "Search text")
    if not ok:
        return jsonify({"error": q}), 400
    if q:
        q_filter["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    status = request.args.get("status", "").strip()
    if status:
        q_filter["status"] = status
    priority = request.args.get("priority", "").strip()
    if priority:
        q_filter["priority"] = priority
    project_id = _oid(request.args.get("project_id", ""))
    if project_id:
        q_filter["project_id"] = project_id
    tasks = list(get_db().tasks.find(q_filter))
    projects_by_id = {str(p["_id"]): p["name"] for p in get_db().projects.find()}
    return jsonify([
        {
            "id": str(t["_id"]),
            "title": t.get("title", ""),
            "status": t.get("status", "Pending"),
            "priority": t.get("priority", "Medium"),
            "project": projects_by_id.get(str(t.get("project_id")), "No project"),
        }
        for t in tasks
    ])


@app.route("/api/report/<report_type>")
@login_required
def api_report(report_type):
    from collections import Counter
    db = get_db()
    lines = []
    if report_type == "tasks":
        tasks = list(db.tasks.find())
        c = Counter(t.get("status", "Pending") for t in tasks)
        lines = [f"{k}: {v} tasks" for k, v in c.items()]
    elif report_type == "projects":
        for p in db.projects.find():
            n = db.tasks.count_documents({"project_id": p["_id"]})
            lines.append(f"{p['name']}: {n} tasks")
    elif report_type == "users":
        for u in db.users.find():
            n = db.tasks.count_documents({"assigned_to": u["_id"]})
            lines.append(f"{u['username']}: {n} tasks assigned")
    return jsonify({"lines": lines})


@app.route("/export/csv")
@login_required
def export_csv():
    db = get_db()
    tasks = list(db.tasks.find())
    projects_by_id = {str(p["_id"]): p["name"] for p in db.projects.find()}
    users_by_id = {str(u["_id"]): u["username"] for u in db.users.find()}
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Title", "Status", "Priority", "Project", "Assigned", "Due"])
    for t in tasks:
        pid = str(t.get("project_id")) if t.get("project_id") else None
        aid = str(t.get("assigned_to")) if t.get("assigned_to") else None
        dd = t.get("due_date")
        due_str = dd.isoformat() if isinstance(dd, date) and dd else (str(dd)[:10] if dd else "")
        w.writerow([
            str(t["_id"]),
            t.get("title", ""),
            t.get("status", "Pending"),
            t.get("priority", "Medium"),
            projects_by_id.get(pid, "No project"),
            users_by_id.get(aid, "Unassigned"),
            due_str,
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="tasks_export.csv",
    )


def _add_history(task_id, action, old_value, new_value):
    get_db().history.insert_one({
        "task_id": task_id,
        "user_id": get_current_user()["_id"],
        "action": action,
        "old_value": old_value,
        "new_value": new_value,
        "timestamp": datetime.utcnow(),
    })


def _add_notification(user_id, message, type_="info"):
    get_db().notifications.insert_one({
        "user_id": user_id,
        "message": message,
        "type": type_,
        "read": False,
        "created_at": datetime.utcnow(),
    })


if __name__ == "__main__":
    try:
        init_db()
        seed_collections()
    except ServerSelectionTimeoutError:
        import sys
        print("\n  Cannot connect to MongoDB.", file=sys.stderr)
        print("  Set MONGODB_URI in your .env file or environment.", file=sys.stderr)
        print("  Example (MongoDB Atlas): MONGODB_URI=mongodb+srv://USER:PASSWORD@cluster.mongodb.net/taskmanager", file=sys.stderr)
        print("  Example (local):         MONGODB_URI=mongodb://localhost:27017/taskmanager  (requires MongoDB running)\n", file=sys.stderr)
        sys.exit(1)
    app.run(debug=True, port=5000)
