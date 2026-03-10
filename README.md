<div align="center">
  <img src="static/images/logo.png" alt="GYMprogrm Logo" width="180"/>

  <h1>GYMprogrm</h1>

  <p><strong>AI-powered web app for personal trainers.</strong><br/>
  Manage clients · Generate programs · Analyze blood tests · Track progress.</p>

  ![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
  ![Django](https://img.shields.io/badge/Django-5.2-green?logo=django)
  ![Claude](https://img.shields.io/badge/AI-Claude%20Sonnet%204.6-purple?logo=anthropic)
  ![Deploy](https://img.shields.io/badge/Deploy-Railway%20%2F%20Render-black?logo=railway)

  **🌐 Live at [gymprogrm.org](https://gymprogrm.org)**

</div>

---

## Purpose

Personal trainers work with real people — each one with different goals, health conditions, and blood results. Keeping track of all of that across spreadsheets and messaging apps is slow and error-prone.

**GYMprogrm** centralizes everything in one place:

- The **trainer** gets a smart dashboard to manage clients, generate personalized programs using AI, and make sense of blood test data in seconds instead of hours.
- The **client** gets a clean portal to view their program, log workouts, and track measurements — accessible on any device.

The AI doesn't replace the trainer's judgment — it does the heavy lifting of structuring information so the trainer can focus on the human side of coaching.

---

## Screenshots

### Trainer Dashboard — Student List
![Student List](docs/screenshots/student_list.png)

### Student Profile — Blood Test Analysis
![Blood Analysis](docs/screenshots/blood_analysis.png)

### AI Program Generation
![Program Generation](docs/screenshots/program_generate.png)

### Program Detail — Workout Days & Nutrition Plan
![Program Detail](docs/screenshots/program_detail.png)

### Exercise Library
![Exercise Library](docs/screenshots/exercise_library.png)

### Client Portal — My Program
![Client Portal](docs/screenshots/client_portal.png)

> **To add screenshots:** take a screenshot of each page, save it to `docs/screenshots/` with the matching filename, then push to GitHub.

---

## Features

### For the trainer

**Client management**
- Create and edit student profiles (goals, health issues, measurements, contact info)
- Upload student photos
- Public intake form — clients fill it in themselves, trainer reviews and accepts

**AI program generation**
- Input: student profile + goals + health issues + blood test (optional)
- Output: multi-day workout program with exercise names (EN + RU), sets/reps, reasoning per exercise
- Separate nutrition plan — daily calories, macros, 4 meals with foods and portions, fasting recommendation, supplements
- Trainer reviews each exercise suggestion and confirms or skips

**Blood test analysis**
- Upload PDF or image of any blood test
- Claude reads every abnormal marker, identifies deficiencies, flags urgent values
- Produces exercise and nutrition recommendations based on the actual lab results
- Key findings are automatically written to the student's health issues field

**Exercise library**
- Filter by muscle group (glutes, legs, back, chest, shoulders, arms, core, cardio)
- AI-generated exercise illustrations (DALL-E 3) with posture tips (Claude Haiku)
- Add any exercise to a specific program day with one click

### For the client

- View current workout program by day
- Log each session — sets, reps, weight per exercise
- Track body measurements over time (weight, body fat %, waist, hips, chest, arms, legs)
- See full workout history

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 + Python 3.11 |
| Database | PostgreSQL (production) / SQLite (dev) |
| AI — programs & analysis | Anthropic Claude Sonnet 4.6 |
| AI — posture tips & text | Anthropic Claude Haiku 4.5 |
| AI — exercise illustrations | OpenAI DALL-E 3 |
| Media storage | Cloudinary |
| Static files | WhiteNoise |
| Server | Gunicorn (gthread, 4 threads, 300 s timeout) |
| Deployment | Railway / Render |

---

## Project structure

```
GYMprogrm/
├── students/          # Profiles, intake, invite system, blood analysis
├── programs/          # Programs, exercise library, AI generation
├── progress/          # Workout logs per session
├── measurements/      # Body measurements over time
├── gymprogrm/         # Settings, URLs, WSGI
├── templates/         # All HTML (trainer + client portal)
├── static/            # CSS, JS, images
├── docs/screenshots/  # README screenshots
├── Procfile           # Gunicorn start command
├── railway.json       # Railway deploy config
└── render.yaml        # Render deploy config
```

---

## Data model

```
Student
  ├── WorkoutProgram
  │     └── ProgramDay
  │           └── ProgramExercise ── ExerciseLibrary
  ├── WorkoutLog
  │     └── ExerciseLog
  └── BodyMeasurement
```

---

## Local setup

```bash
git clone https://github.com/Liliyalexx/GYMprogrm.git
cd GYMprogrm
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Create .env (see Environment variables below)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://localhost:8000` and log in as the superuser (trainer account).

---

## Environment variables

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=                       # leave blank → uses SQLite locally
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=               # https://yourapp.railway.app

ANTHROPIC_API_KEY=                  # required — program generation & blood analysis
OPENAI_API_KEY=                     # required — exercise illustrations

CLOUDINARY_URL=                     # optional — cloud media storage
```

---

## Deployment

### Railway

1. Connect this repo in Railway
2. Add a PostgreSQL database plugin
3. Set the environment variables under **Variables**
4. Push to `main` — Railway builds and deploys automatically

`railway.json` handles the build and start commands.

### Render

1. Go to **Render → New → Blueprint**
2. Connect this repo — `render.yaml` is detected automatically (includes PostgreSQL)
3. Set `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `CLOUDINARY_URL` manually
4. Deploy

---

## After every push

Both platforms deploy automatically on push to `main`. Watch for:

```
✓ pip install -r requirements.txt
✓ python manage.py collectstatic
✓ python manage.py migrate
✓ Gunicorn started on port $PORT
```

If a step fails the previous version stays live — check the deploy logs for the exact error.

---

## License

Private project. All rights reserved.
