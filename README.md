# GYMprogrm

> AI-powered personal trainer web app — manage clients, generate workout programs, analyze blood tests, and track progress.

---

## What it does

A full-stack Django application built for a single personal trainer. The trainer gets a powerful dashboard; clients get their own portal to log workouts and measurements.

| Trainer side | Client side |
|---|---|
| Manage student profiles | View assigned program |
| Generate AI workout programs | Log sets / reps / weight |
| Analyze blood tests with AI | Track body measurements |
| Review client intake forms | See workout history |
| Browse & assign exercises | — |

---

## Key features

### AI Program Generation
Sends the student's profile, goals, health issues, and blood test (PDF or image) to Claude. Gets back a full multi-day workout program with Russian exercise names, reasons for each exercise, and a complete nutrition plan — macros, meals, supplements, fasting recommendation.

### Blood Test Analysis
Upload a PDF or photo of a blood test. Claude reads every abnormal marker, identifies deficiencies, and produces exercise and nutrition recommendations tailored to the findings. Results are saved to the student's health profile automatically.

### Exercise Library
Hundreds of exercises organized by muscle group. Each exercise can have an AI-generated cartoon illustration (DALL-E 3) and posture tips (Claude Haiku). Exercises can be added to any program day directly from the library.

### Client Portal
Students get their own login via an invite link. They see their current program, log workouts session by session, and track body measurements over time.

### Intake Forms
A public form (no login needed) lets potential clients fill in their info and upload a blood test. The trainer reviews pending submissions and accepts them with one click.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 + Python 3.11 |
| Database | PostgreSQL (production) / SQLite (dev) |
| AI — programs & analysis | Anthropic Claude Sonnet 4.6 |
| AI — exercise illustrations | OpenAI DALL-E 3 |
| Media storage | Cloudinary |
| Static files | WhiteNoise |
| Server | Gunicorn (gthread, 4 threads, 300s timeout) |
| Deployment | Railway / Render |

---

## Project structure

```
GYMprogrm/
├── students/          # Student profiles, intake, blood analysis
├── programs/          # Workout programs, exercise library, AI generation
├── progress/          # Workout logs
├── measurements/      # Body measurements over time
├── gymprogrm/         # Django settings, URLs, WSGI
├── templates/         # All HTML templates
├── static/            # CSS, JS, images
├── Procfile           # Gunicorn start command
├── railway.json       # Railway deploy config
└── render.yaml        # Render deploy config
```

---

## Local setup

```bash
# 1. Clone and create virtual environment
git clone https://github.com/Liliyalexx/GYMprogrm.git
cd GYMprogrm
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and fill in your keys (see below)

# 4. Run migrations and create trainer account
python manage.py migrate
python manage.py createsuperuser

# 5. Start the dev server
python manage.py runserver
```

Open `http://localhost:8000` and log in with the superuser credentials.

---

## Environment variables

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=                    # leave empty for SQLite in dev
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=            # e.g. https://yourapp.railway.app

ANTHROPIC_API_KEY=               # required for program generation & blood analysis
OPENAI_API_KEY=                  # required for exercise illustrations

CLOUDINARY_URL=                  # optional — enables cloud media storage
```

---

## Deployment

### Railway
The `railway.json` file configures the build and start commands automatically.

1. Push to GitHub
2. Connect the repo in Railway
3. Add a PostgreSQL plugin
4. Set all environment variables in Railway → Variables
5. Deploy — migrations run automatically on every deploy

### Render
The `render.yaml` file configures everything including a managed PostgreSQL database.

1. Push to GitHub
2. Go to Render → New → Blueprint
3. Connect the repo — Render detects `render.yaml` automatically
4. Set the three secret variables manually (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `CLOUDINARY_URL`)
5. Deploy

---

## After every code push

Railway and Render both trigger a deploy automatically when you push to `main`. Watch the build logs to confirm:

```
✓ pip install -r requirements.txt
✓ python manage.py collectstatic
✓ python manage.py migrate
✓ Gunicorn started on port $PORT
```

If a step fails the old version stays live. Check the deploy logs in the Railway or Render dashboard for the exact error.

---

## Models overview

```
Student ──────────── WorkoutProgram ── ProgramDay ── ProgramExercise
    │                                                       │
    │                                               ExerciseLibrary
    │
    ├── WorkoutLog ── ExerciseLog
    └── BodyMeasurement
```

---

## API integrations

| Service | Used for | Model |
|---|---|---|
| Anthropic | Workout program generation | claude-sonnet-4-6 |
| Anthropic | Blood test analysis | claude-sonnet-4-6 |
| Anthropic | Exercise posture tips | claude-haiku-4-5 |
| Anthropic | Text correction (health/goals) | claude-haiku-4-5 |
| OpenAI | Exercise illustrations | dall-e-3 |
| Cloudinary | Student photos, blood test PDFs | — |

---

## License

Private project. All rights reserved.
