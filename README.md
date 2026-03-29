# blogg-sphere

A full-featured blogging platform built with Flask, deployed on Vercel with a Neon PostgreSQL database. Supports rich content authoring, social interactions, real-time notifications, and an admin panel.

**Live:** [blogg-sphere](https://blogg-sphere.vercel.app)

---

## Features

**Content**
- Create, edit, and soft-delete posts with titles and markdown-rendered bodies (up to 5000 chars)
- Tag posts with up to 5 comma-separated tags; click any tag to browse related posts
- Threaded comments with one level of replies; markdown support; soft-delete

**Social**
- Follow / unfollow users; personalised home feed shows followed users' posts
- Like / unlike posts with real-time count update (no page reload)
- In-app notifications for follows, likes, comments, and replies

**Discovery**
- Search posts by title or body
- Trending page ranked by total likes + comments (all-time)
- Explore page showing all posts chronologically

**User Accounts**
- Registration, login, password reset via email
- Edit profile (username, bio)
- Change password (requires current password confirmation)
- Change email
- Upload profile picture via Cloudinary (falls back to Gravatar)
- Soft-delete account

**UX**
- Bootstrap 5 responsive layout
- Dark / Light / System theme toggle (persisted in `localStorage`)
- Flash messages with appropriate severity colours

**Admin**
- Admin dashboard with user, post, and comment counts
- Manage users: view all, activate / deactivate accounts
- Manage posts: view all (including deleted), restore or soft-delete
- Manage comments: view all, restore or soft-delete
- Grant admin via CLI: `python -m flask make-admin <username>`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask 2.2 |
| ORM / Migrations | SQLAlchemy, Flask-Migrate (Alembic) |
| Database | Neon PostgreSQL (prod), SQLite (dev) |
| Auth | Flask-Login, Flask-WTF (CSRF) |
| Email | Flask-Mail (Gmail SMTP) |
| Image Storage | Cloudinary |
| Markdown | mistune + bleach (XSS sanitisation) |
| i18n | Flask-Babel |
| Frontend | Bootstrap 5, Bootstrap Icons, Font Awesome 4 |
| Deployment | Vercel (serverless) |

---

## Local Development

### Prerequisites

- Python 3.10+
- Git

### Setup

```bash
git clone <your-repository-url>
cd blogApp

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Environment

Create a `.flaskenv` file in the project root (never commit this):

```
FLASK_APP=blogApp.py
FLASK_DEBUG=1
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
```

The app falls back to a local `app.db` SQLite file when `DATABASE_URL` is not set.

### Database

```bash
python -m flask db upgrade
```

### Run

```bash
python -m flask run
```

Visit `http://localhost:5000`.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes (prod) | Flask secret key for session signing |
| `DATABASE_URL` | Yes (prod) | PostgreSQL connection string (Neon) |
| `CLOUDINARY_URL` | Yes | Cloudinary connection string for avatar uploads |
| `MAIL_SERVER` | Optional | SMTP server (e.g. `smtp.gmail.com`) |
| `MAIL_PORT` | Optional | SMTP port (default `587`) |
| `MAIL_USE_TLS` | Optional | Set to `1` to enable TLS |
| `MAIL_USERNAME` | Optional | SMTP username |
| `MAIL_PASSWORD` | Optional | SMTP app password |
| `ADMIN_EMAIL` | Optional | Email for error notifications |

Set all production variables in the Vercel dashboard under **Settings → Environment Variables**.

---

## Deployment (Vercel + Neon)

### 1. Run migrations against Neon

```powershell
# PowerShell
$env:DATABASE_URL="postgresql://..."; python -m flask db upgrade
```

### 2. Push to git

```bash
git add -A
git commit -m "your message"
git push
```

Vercel deploys automatically on push. Always run migrations **before** pushing code that requires schema changes.

---

## Admin Setup

Grant admin privileges to a user (run against the target database):

```bash
# Local
python -m flask make-admin <username>

# Against Neon (PowerShell)
$env:DATABASE_URL="postgresql://..."; python -m flask make-admin <username>
```

Revoke with:

```bash
python -m flask revoke-admin <username>
```

---

## Project Structure

```
blogApp/
├── app/
│   ├── templates/
│   │   ├── admin/          # Admin panel templates
│   │   └── email/          # Email templates
│   ├── __init__.py         # App factory, extensions
│   ├── models.py           # SQLAlchemy models
│   ├── routes.py           # All route handlers
│   ├── forms.py            # Flask-WTF forms
│   ├── utils.py            # Markdown renderer
│   ├── email.py            # Email helpers
│   ├── errors.py           # Error handlers
│   └── cli.py              # CLI commands
├── migrations/             # Alembic migration scripts
├── config.py               # Configuration class
├── blogApp.py              # Application entry point
├── requirements.txt
└── vercel.json
```

---

## Running Tests

```bash
python -m pytest tests.py -v
```


