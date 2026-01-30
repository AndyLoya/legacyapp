# Task Manager (Flask + MongoDB)

A simple task and project manager with Flask and MongoDB.

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set your MongoDB connection URL**

   - **Option A – environment variable**

     ```bash
     # Linux/macOS
     export MONGODB_URI="mongodb://localhost:27017/taskmanager"

     # Windows (PowerShell)
     $env:MONGODB_URI="mongodb://localhost:27017/taskmanager"
     ```

   - **Option B – `.env` file (recommended)**

     Copy the example and edit:

     ```bash
     cp .env.example .env
     ```

     Then set `MONGODB_URI` in `.env`, for example:

     - Local: `MONGODB_URI=mongodb://localhost:27017/taskmanager`
     - MongoDB Atlas: `MONGODB_URI=mongodb+srv://USER:PASSWORD@cluster.mongodb.net/taskmanager`

3. **Run the app**

   ```bash
   python app.py
   ```

   Open http://127.0.0.1:5000 and sign in with **admin** / **admin**.

On first run, the app creates the database and collections and seeds default users and projects if they are empty.
