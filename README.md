# Honeypot Virtualization System

A web-based honeypot simulation: a fake Linux server in the browser. Visitors get a virtual shell, explore a virtual file system, and hunt for hidden CTF flags — while every command they type is logged and watched live from an admin dashboard.

This is a safe, self-contained simulation for learning and CTF practice. No real system is exposed.

## What it does

Open the app and you land on a login page. Once in, you get a terminal connected to a virtual shell that pretends to be an Ubuntu server. You can move around the file system, read files, and run commands. Ten flags are hidden in the virtual file system — find one with `cat` and it is captured automatically, or submit it with the `submit` command. Your score is tracked live.

An admin dashboard shows every connected session, a live feed of all commands typed, and the scoreboard. From the dashboard the admin can kick or ban a session, send a message to a user, run a command on a user's terminal, rename a user, and unban IPs.

## Features

- Virtual shell with an in-memory Linux-like file system (`/home/user`, `/etc`, `/var/log`, `/root`, `/tmp`, …)
- Shell commands: `ls`, `cd`, `cat`, `mkdir`, `echo`, `rm`, `touch`, `history`, `sudo`, `scan`, `trace`, `decrypt`, `ifconfig`, `netstat`, `ps`, `score`, `submit`, `msg`, `clear`, `exit`
- CTF mode: 10 hidden flags worth 440 points in total, from Easy (10 pts) to Expert (100 pts)
- Automatic flag capture when a flag file is read with `cat`, plus manual `submit`
- Live scoreboard with per-player score and flags found
- Admin dashboard: live sessions, command log feed, scores, kick/ban/message/execute/rename/unban
- Every command is logged with timestamp, IP address, session id and working directory (`GET /api/logs`)
- REST endpoints for the admin view: `/api/logs`, `/api/flags`, `/api/scores`
- Real-time terminal over WebSockets (Flask-SocketIO), one separate shell per connected session
- Login page as the entry point, with separate admin pages (`admin.html`, `admin-login.html`)

## Tech stack

- Python, Flask — web server and API
- Flask-SocketIO — real-time terminal
- Flask-CORS
- eventlet — async server
- HTML, CSS, JavaScript — frontend terminal and admin dashboard

## How to run

You need Python 3.

```bash
cd backend
pip install -r requirements.txt
python app.py
```

For any deployment outside your own machine, set a secret key first — the built-in default is for local development only:

```bash
SECRET_KEY=<a-long-random-value> python app.py
```

Then open http://127.0.0.1:5000/ in your browser. The login page is the entry point; the terminal opens after you enter the app.

To try the CTF, open the terminal and explore — for example:

```bash
ls -a
cat user.txt
score
```

The full flag list and hints are in `CTF_FLAGS_GUIDE.txt`.

## Project structure

```
Honeypot-Virtualization-System/
├── backend/
│   ├── app.py              # Flask + Socket.IO server, API routes, admin actions, session handling
│   ├── simulator.py        # VirtualShell: virtual file system, shell commands, CTF flags and scoring
│   ├── test_client.py      # Test client for the backend
│   └── requirements.txt    # flask, flask-socketio, flask-cors, eventlet
├── frontend/
│   ├── login.html          # Entry-point login page
│   ├── index.html          # Terminal page
│   ├── admin.html          # Admin dashboard: sessions, logs, scores
│   ├── admin-login.html    # Admin login page
│   ├── app.js              # Terminal and dashboard client logic
│   └── style.css           # Frontend styling
├── CTF_FLAGS_GUIDE.txt     # All 10 flags, points, difficulty, hints and how to submit
└── README.md               # This file
```
