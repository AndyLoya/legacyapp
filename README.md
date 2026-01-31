# Task Manager

A web-based task and project management application built with **Flask** and **MongoDB**. Manage tasks, projects, comments, and user accounts from a single dashboard.

---

## Features

- **Task Management** — Create, edit, and delete tasks with title, description, status, priority, due date, and assignment
- **Project Management** — Organize tasks by project with expandable descriptions
- **Comments** — Add comments to tasks
- **Change History** — View task change history
- **Notifications** — In-app notifications for task updates and assignments
- **Search** — Filter tasks by text, status, priority, and project
- **Reports** — Generate tasks, projects, and users reports; export to CSV
- **User Management (Admin)** — Admin users can create, edit, and delete users (username/password)
- **Profile** — Any user can change their own password from the header menu
- **Permissions** — Users can only edit/delete tasks they created or are assigned to; admins have full access

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

| Username | Password | Role  |
|----------|----------|-------|
| `admin`  | `admin`   | Admin (full access, user management) |
| `user1`  | `user1`   | User  |
| `user2`  | `user2`   | User  |

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

## Production Notes

- Set a strong, random `SECRET_KEY` in the environment.
- Use a production WSGI server (e.g. **Gunicorn** with a reverse proxy) instead of the built-in Flask server.
- Ensure MongoDB is secured (authentication, network access) and use TLS for connections when possible.
- Consider running the app over HTTPS.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| **"Cannot connect to MongoDB"** | Ensure MongoDB is running (local) or that `MONGODB_URI` is correct and the Atlas cluster allows your IP. |
| **Port 5000 in use** | Edit `app.py` and change the port in `app.run(debug=True, port=5000)` or set the `PORT` environment variable if your runner supports it. |
| **Module not found** | Activate the virtual environment and run `pip install -r requirements.txt` again. |

---

## License

Use and modify as needed for your project.
