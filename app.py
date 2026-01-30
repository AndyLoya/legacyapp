"""Task Manager - Flask application."""
import os
import csv
import io
from datetime import datetime, date
from functools import wraps

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

from models import db, User, Project, Task, Comment, HistoryEntry, Notification

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///taskmanager.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def get_current_user():
    """Current user from session."""
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])


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


def init_db():
    """Create tables and seed initial data if missing."""
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            for u in [
                ("admin", "admin"),
                ("user1", "user1"),
                ("user2", "user2"),
            ]:
                db.session.add(User(username=u[0], password=u[1]))
            for p in [
                ("Demo Project", "Sample project"),
                ("Alpha Project", "Main project"),
                ("Beta Project", "Secondary project"),
            ]:
                db.session.add(Project(name=p[0], description=p[1]))
            db.session.commit()


# ---------- Auth routes ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
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
    projects = Project.query.order_by(Project.name).all()
    users = User.query.order_by(User.username).all()
    tasks = Task.query.all()
    stats = _compute_stats(tasks)
    return render_template(
        "dashboard.html",
        tab=tab,
        projects=projects,
        users=users,
        tasks=tasks,
        stats=stats,
    )


def _compute_stats(tasks):
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "Completed")
    pending = total - completed
    high_priority = sum(
        1 for t in tasks if t.priority in ("High", "Critical")
    )
    overdue = 0
    today = date.today()
    for t in tasks:
        if t.due_date and t.status != "Completed" and t.due_date < today:
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
    title = request.form.get("task_title", "").strip()
    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    try:
        due = request.form.get("task_due_date")
        due_date = datetime.strptime(due, "%Y-%m-%d").date() if due else None
    except ValueError:
        due_date = None
    raw_project = request.form.get("task_project_id") or ""
    raw_assigned = request.form.get("task_assigned_to") or ""
    task = Task(
        title=title,
        description=request.form.get("task_description", ""),
        status=request.form.get("task_status", "Pending"),
        priority=request.form.get("task_priority", "Medium"),
        project_id=int(raw_project) if raw_project else None,
        assigned_to=int(raw_assigned) if raw_assigned else None,
        due_date=due_date,
        estimated_hours=float(request.form.get("task_hours") or 0),
        created_by=get_current_user().id,
    )
    db.session.add(task)
    db.session.flush()
    _add_history(task.id, "CREATED", "", task.title)
    if task.assigned_to:
        _add_notification(
            task.assigned_to,
            f"New task assigned: {task.title}",
            "task_assigned",
        )
    db.session.commit()
    flash("Task created.", "success")
    return redirect(url_for("dashboard", tab="tasks"))


@app.route("/task/update/<int:task_id>", methods=["POST"])
@login_required
def task_update(task_id):
    task = Task.query.get_or_404(task_id)
    title = request.form.get("task_title", "").strip()
    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("dashboard", tab="tasks"))
    old_status = task.status
    old_title = task.title
    try:
        due = request.form.get("task_due_date")
        due_date = datetime.strptime(due, "%Y-%m-%d").date() if due else None
    except ValueError:
        due_date = task.due_date
    task.title = title
    task.description = request.form.get("task_description", "")
    task.status = request.form.get("task_status", "Pending")
    task.priority = request.form.get("task_priority", "Medium")
    raw_project = request.form.get("task_project_id") or ""
    raw_assigned = request.form.get("task_assigned_to") or ""
    task.project_id = int(raw_project) if raw_project else None
    task.assigned_to = int(raw_assigned) if raw_assigned else None
    task.due_date = due_date
    task.estimated_hours = float(request.form.get("task_hours") or 0)
    if old_status != task.status:
        _add_history(task.id, "STATUS_CHANGED", old_status, task.status)
    if old_title != task.title:
        _add_history(task.id, "TITLE_CHANGED", old_title, task.title)
    if task.assigned_to:
        _add_notification(
            task.assigned_to,
            f"Task updated: {task.title}",
            "task_updated",
        )
    db.session.commit()
    flash("Task updated.", "success")
    return redirect(url_for("dashboard", tab="tasks"))


@app.route("/task/delete/<int:task_id>", methods=["POST"])
@login_required
def task_delete(task_id):
    task = Task.query.get_or_404(task_id)
    title = task.title
    _add_history(task.id, "DELETED", title, "")
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("dashboard", tab="tasks"))


# ---------- Projects ----------

@app.route("/project/add", methods=["POST"])
@login_required
def project_add():
    name = request.form.get("project_name", "").strip()
    if not name:
        flash("Project name is required.", "error")
        return redirect(url_for("dashboard", tab="projects"))
    db.session.add(Project(name=name, description=request.form.get("project_description", "")))
    db.session.commit()
    flash("Project created.", "success")
    return redirect(url_for("dashboard", tab="projects"))


@app.route("/project/update/<int:project_id>", methods=["POST"])
@login_required
def project_update(project_id):
    project = Project.query.get_or_404(project_id)
    name = request.form.get("project_name", "").strip()
    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("dashboard", tab="projects"))
    project.name = name
    project.description = request.form.get("project_description", "")
    db.session.commit()
    flash("Project updated.", "success")
    return redirect(url_for("dashboard", tab="projects"))


@app.route("/project/delete/<int:project_id>", methods=["POST"])
@login_required
def project_delete(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Project deleted.", "success")
    return redirect(url_for("dashboard", tab="projects"))


# ---------- Comments ----------

@app.route("/comment/add", methods=["POST"])
@login_required
def comment_add():
    try:
        task_id = int(request.form.get("comment_task_id"))
    except (TypeError, ValueError):
        flash("Invalid task ID.", "error")
        return redirect(url_for("dashboard", tab="comments"))
    text = request.form.get("comment_text", "").strip()
    if not text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("dashboard", tab="comments"))
    if not Task.query.get(task_id):
        flash("Task not found.", "error")
        return redirect(url_for("dashboard", tab="comments"))
    db.session.add(
        Comment(task_id=task_id, user_id=get_current_user().id, comment_text=text)
    )
    db.session.commit()
    flash("Comment added.", "success")
    return redirect(url_for("dashboard", tab="comments"))


# ---------- Notifications ----------

@app.route("/notifications/read", methods=["POST"])
@login_required
def notifications_mark_read():
    Notification.query.filter_by(user_id=get_current_user().id).update({"read": True})
    db.session.commit()
    flash("Notifications marked as read.", "success")
    return redirect(url_for("dashboard", tab="notifications"))


# ---------- API / datos para AJAX ----------

@app.route("/api/task/<int:task_id>")
@login_required
def api_task(task_id):
    task = Task.query.get_or_404(task_id)
    return jsonify({
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "status": task.status,
        "priority": task.priority,
        "project_id": task.project_id or 0,
        "assigned_to": task.assigned_to or 0,
        "due_date": task.due_date.isoformat() if task.due_date else "",
        "estimated_hours": task.estimated_hours,
    })


@app.route("/api/comments/<int:task_id>")
@login_required
def api_comments(task_id):
    comments = Comment.query.filter_by(task_id=task_id).order_by(Comment.created_at).all()
    users = {u.id: u.username for u in User.query.all()}
    return jsonify([
        {
            "id": c.id,
            "user": users.get(c.user_id, "?"),
            "text": c.comment_text,
            "created_at": c.created_at.isoformat(),
        }
        for c in comments
    ])


@app.route("/api/history")
@app.route("/api/history/<int:task_id>")
@login_required
def api_history(task_id=None):
    q = HistoryEntry.query.order_by(HistoryEntry.timestamp.desc())
    if task_id is not None:
        q = q.filter_by(task_id=task_id)
    entries = q.limit(100).all()
    users = {u.id: u.username for u in User.query.all()}
    return jsonify([
        {
            "id": e.id,
            "task_id": e.task_id,
            "user": users.get(e.user_id, "?"),
            "action": e.action,
            "old_value": e.old_value or "",
            "new_value": e.new_value or "",
            "timestamp": e.timestamp.isoformat(),
        }
        for e in entries
    ])


@app.route("/api/notifications")
@login_required
def api_notifications():
    notifs = Notification.query.filter_by(
        user_id=get_current_user().id, read=False
    ).order_by(Notification.created_at.desc()).all()
    return jsonify([
        {"id": n.id, "message": n.message, "type": n.type, "created_at": n.created_at.isoformat()}
        for n in notifs
    ])


@app.route("/api/search")
@login_required
def api_search():
    q = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    try:
        project_id = int(request.args.get("project_id", 0))
    except ValueError:
        project_id = 0
    tasks = Task.query
    if q:
        tasks = tasks.filter(
            db.or_(
                Task.title.ilike(f"%{q}%"),
                Task.description.ilike(f"%{q}%"),
            )
        )
    if status:
        tasks = tasks.filter(Task.status == status)
    if priority:
        tasks = tasks.filter(Task.priority == priority)
    if project_id:
        tasks = tasks.filter(Task.project_id == project_id)
    tasks = tasks.all()
    projects = {p.id: p.name for p in Project.query.all()}
    return jsonify([
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "project": projects.get(t.project_id) or "No project",
        }
        for t in tasks
    ])


@app.route("/api/report/<report_type>")
@login_required
def api_report(report_type):
    if report_type == "tasks":
        tasks = Task.query.all()
        from collections import Counter
        c = Counter(t.status or "Pending" for t in tasks)
        lines = [f"{k}: {v} tasks" for k, v in c.items()]
    elif report_type == "projects":
        projects = Project.query.all()
        lines = []
        for p in projects:
            n = Task.query.filter_by(project_id=p.id).count()
            lines.append(f"{p.name}: {n} tasks")
    elif report_type == "users":
        users = User.query.all()
        lines = []
        for u in users:
            n = Task.query.filter_by(assigned_to=u.id).count()
            lines.append(f"{u.username}: {n} tasks assigned")
    else:
        return jsonify({"lines": []})
    return jsonify({"lines": lines})


@app.route("/export/csv")
@login_required
def export_csv():
    tasks = Task.query.all()
    projects = {p.id: p.name for p in Project.query.all()}
    users = {u.id: u.username for u in User.query.all()}
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Title", "Status", "Priority", "Project", "Assigned", "Due"])
    for t in tasks:
        w.writerow([
            t.id,
            t.title,
            t.status or "Pending",
            t.priority or "Medium",
            projects.get(t.project_id) or "No project",
            users.get(t.assigned_to) or "Unassigned",
            t.due_date.isoformat() if t.due_date else "",
        ])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="tasks_export.csv",
    )


def _add_history(task_id, action, old_value, new_value):
    db.session.add(
        HistoryEntry(
            task_id=task_id,
            user_id=get_current_user().id,
            action=action,
            old_value=old_value,
            new_value=new_value,
        )
    )


def _add_notification(user_id, message, type_="info"):
    db.session.add(
        Notification(user_id=user_id, message=message, type=type_)
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
