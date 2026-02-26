# GYMprogrm — Claude Project Context

## Project Overview
A personal trainer web app to manage students, assign workout programs, and track progress over time.

## Owner
Personal trainer (single user — trainer only).

---

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Django (Python) |
| Frontend | Django templates + CSS + React (islands pattern) |
| Database | PostgreSQL (production) / SQLite (development) |
| Auth | Django built-in auth — trainer login only |
| Deployment | Railway or Render (cloud, free tier) |
| Static files | WhiteNoise |

---

## Core Features
1. **Student profiles** — name, age, goals, contact info, notes
2. **Workout programs** — create programs, assign them to students, define exercises, sets, reps
3. **Progress tracking** — log completed workouts with actual weights/reps per session
4. **Body measurements** — log weight, body fat %, and custom measurements (chest, waist, hips, etc.) over time

---

## App Architecture

### Django Apps
- `students` — Student model, profiles, notes
- `programs` — WorkoutProgram, Exercise, ProgramDay models
- `progress` — WorkoutLog, ExerciseLog (actual session data)
- `measurements` — BodyMeasurement model (weight, body fat, custom fields)

### Key Models (planned)
```
Student
  - name, email, phone, date_of_birth
  - goal (text), notes
  - created_at, is_active

WorkoutProgram
  - name, description
  - student (FK)
  - created_at, is_active

ProgramDay
  - program (FK), day_number, name (e.g. "Day A - Push")

Exercise
  - program_day (FK), name, sets, reps, rest_seconds, notes

WorkoutLog
  - student (FK), date, notes

ExerciseLog
  - workout_log (FK), exercise_name, sets_done, reps_done, weight_kg, notes

BodyMeasurement
  - student (FK), date, weight_kg, body_fat_pct
  - chest_cm, waist_cm, hips_cm, arms_cm, legs_cm
```

---

## Project Conventions
- Python: follow PEP 8
- Templates: extend `base.html`, use `{% block %}` pattern
- CSS: separate file per app/section, fully responsive (mobile-first media queries)
- URLs: namespaced per app (`app_name = 'students'`, etc.)
- React (islands pattern) for interactive widgets — mount into `<div id="root">` or named mount points in Django templates; Django still owns routing and auth
- Build React with Vite; output bundled JS/CSS into `static/` so Django/WhiteNoise can serve it
- Forms: Django ModelForms with validation
- Date format: ISO 8601 (YYYY-MM-DD) throughout

---

## Development Setup
```bash
# Virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (trainer account)
python manage.py createsuperuser

# Run dev server
python manage.py runserver
```

## Environment Variables
```
SECRET_KEY=
DEBUG=True
DATABASE_URL=          # set in production
ALLOWED_HOSTS=
```

---

## Deployment (Railway / Render)
- Use `gunicorn` as WSGI server
- Static files served via WhiteNoise
- `DATABASE_URL` env var auto-injected by Railway/Render PostgreSQL add-on
- `Procfile`: `web: gunicorn gymprogrm.wsgi`
- Run `python manage.py collectstatic` as a build step

---

## File Structure (target)
```
GYMprogrm/
├── CLAUDE.md
├── manage.py
├── requirements.txt
├── Procfile
├── .env
├── gymprogrm/          # Django project (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── students/
├── programs/
├── progress/
├── measurements/
└── templates/
    ├── base.html
    └── (per-app subdirs)
```

---

## What to Always Check Before Making Changes
1. Read this file for project context
2. Check which Django app the change belongs to
3. Run `python manage.py check` after model changes
4. Run `python manage.py makemigrations` after model edits
5. Test in browser at `localhost:8000` before considering done

---

## Current Status
- [ ] Project scaffolded
- [ ] `students` app created
- [ ] `programs` app created
- [ ] `progress` app created
- [ ] `measurements` app created
- [ ] Base templates and CSS set up
- [ ] Auth (trainer login) configured
- [ ] Deployed to Railway/Render
