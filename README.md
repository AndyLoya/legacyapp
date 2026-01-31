# Task Manager

A web-based task and project management application built with **Flask** and **MongoDB**. This is the **migrated version** of the original *Task Manager Simple* (JavaScript + localStorage): same functionality, now with a server, database, and multi-user support.

---

## Migration from Original (JavaScript / localStorage)

The original app was a **client-only** system (HTML, CSS, JavaScript) using **localStorage**. This version **migrates** all features to a **Flask backend** with **MongoDB**, so the app runs on a server and data is shared across users and devices.

| Original (JavaScript) | Migrated (Flask + MongoDB) |
|-----------------------|----------------------------|
| No server, runs in browser | Flask server + MongoDB |
| localStorage as database | MongoDB as database |
| Open `index.html` in browser | Run server, open URL in browser |
| Default login: admin / admin | Same: admin / admin (and user1, user2) |

**Feature parity — all original functionalities are implemented:**

| Original feature | Status in this version |
|------------------|------------------------|
| **Authentication** — Login with multiple users | ✅ Login, sessions, multiple users |
| **CRUD Tasks** — Create, read, update, delete tasks | ✅ Full task CRUD with status, priority, due date, assignment |
| **CRUD Projects** — Manage projects | ✅ Full project CRUD |
| **Comments** — Comments on tasks | ✅ Comments per task |
| **History & audit** — Change log | ✅ Task change history |
| **Notifications** — Per-user notifications | ✅ Notifications (updates, assignments) |
| **Advanced search** — Multiple filters | ✅ Search by text, status, priority, project |
| **Reports** — Tasks, projects, users | ✅ Reports + export CSV |
| **Export CSV** | ✅ Export tasks to CSV |

**Additional in this version:** User management (admin), change-own-password, deployable (e.g. Render).

---

## Features

- **Task Management** — Create, edit, and delete tasks (title, description, status, priority, due date, assignment)
- **Project Management** — Organize tasks by project; expandable descriptions in table
- **Comments** — Add comments to tasks
- **Change History** — View task change history and audit log
- **Notifications** — In-app notifications for task updates and assignments
- **Search** — Filter tasks by text, status, priority, and project
- **Reports** — Generate tasks, projects, and users reports; export to CSV
- **User Management (Admin)** — Admin users can create, edit, and delete users (username/password)
- **Profile** — Any user can change their own password from the header menu

---

## Prerequisites

- **Python 3.8+**
- **MongoDB** (local instance or [MongoDB Atlas](https://www.mongodb.com/atlas) account)
- (Optional) **Git** for cloning the repository

---

## Setup Instructions

### 1. Clone or download the project

```bash
git clone <repository-url> taskmanager
cd taskmanager
```

If you don't use Git, download and extract the project into a folder and open a terminal in that folder.

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root (you can copy from the example):

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` and set at least the MongoDB connection string:

| Variable      | Required | Description |
|--------------|----------|-------------|
| `MONGODB_URI` | Yes      | MongoDB connection URL including database name. Examples: local `mongodb://localhost:27017/taskmanager`, Atlas `mongodb+srv://USER:PASSWORD@cluster.mongodb.net/taskmanager` |
| `SECRET_KEY`  | No       | Flask session secret. Defaults to a dev value; **set a strong random value in production**. |

**Example `.env` (local MongoDB):**

```env
MONGODB_URI=mongodb://localhost:27017/taskmanager
```

**Example `.env` (MongoDB Atlas):**

```env
MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@cluster0.xxxxx.mongodb.net/taskmanager?retryWrites=true&w=majority
SECRET_KEY=your-long-random-secret-key
```

Alternatively, you can set `MONGODB_URI` (and `SECRET_KEY`) directly in your shell instead of using a `.env` file:

```bash
# Linux / macOS
export MONGODB_URI="mongodb://localhost:27017/taskmanager"

# Windows (PowerShell)
$env:MONGODB_URI="mongodb://localhost:27017/taskmanager"
```

### 5. Run the application

```bash
python app.py
```

You should see output similar to:

```
 * Running on http://127.0.0.1:5000
```

Open **http://127.0.0.1:5000** in your browser.

### 6. Sign in

On first run, the app seeds the database with default data if collections are empty.

**Default users** (same as the original app):

| Username | Password | Role  |
|----------|----------|-------|
| `admin`  | `admin`   | Admin (full access, user management) |
| `user1`  | `user1`   | User  |
| `user2`  | `user2`   | User  |

**Default projects:** Demo Project, Alpha Project, Beta Project (with sample descriptions).

**Change the default passwords** after first login (admin can change any user; all users can change their own password via the header menu).

---

## Project Structure

```
taskmanager/
├── app.py              # Flask app, routes, and business logic
├── db.py               # MongoDB connection and initialization
├── models.py           # Data model documentation
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── static/
│   ├── css/style.css   # Styles
│   └── js/
│       ├── dashboard.js
│       └── main.js
└── templates/
    ├── base.html
    ├── dashboard.html
    └── login.html
```

---

## Deploy on Render

The app is ready to deploy on [Render](https://render.com) as a Web Service.

1. **Push your code** to a Git repository (e.g. GitHub).

2. In the [Render Dashboard](https://dashboard.render.com), click **New > Web Service** and connect your repo.

3. **Configure the service:**

   | Setting | Value |
   |--------|--------|
   | **Language** | Python 3 |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app` |

4. **Environment variables** (in Render: Environment tab):

   - **MONGODB_URI** (required) — Your MongoDB connection string. Use [MongoDB Atlas](https://www.mongodb.com/atlas) and set the URI; allow access from anywhere (`0.0.0.0/0`) in Atlas Network Access if needed.
   - **SECRET_KEY** (recommended) — A long random string for session security.

5. **Deploy.** Render will build and run the app; it will be available at `https://<your-service>.onrender.com`.

**Note:** Render free tier spins down after inactivity; the first request after idle may be slow. For always-on hosting, use a paid plan.

---

## Production Notes

- Set a strong, random `SECRET_KEY` in the environment.
- On Render, the app runs with **Gunicorn** via the start command above.
- Ensure MongoDB is secured (authentication, network access) and use TLS for connections when possible.
- Render provides HTTPS for your service.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| **"Cannot connect to MongoDB"** | Ensure MongoDB is running (local) or that `MONGODB_URI` is correct and the Atlas cluster allows your IP (or `0.0.0.0/0` for Render). |
| **Port 5000 in use** | Set the `PORT` environment variable; the app uses it when provided (e.g. on Render). |
| **Module not found** | Activate the virtual environment and run `pip install -r requirements.txt` again. |

---

## License

Use and modify as needed for your project.
