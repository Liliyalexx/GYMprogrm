<div align="center">
  <img src="static/images/logo.png" alt="GYMprogrm Logo" width="180"/>

  <h1>GYMprogrm</h1>

  <p><strong>AI-powered web app for personal trainers — and self-serve AI coaching for independent members.</strong><br/>
  Manage clients · Generate programs · Analyze blood tests · Track progress · AI Coach · Installable on any phone.</p>

  ![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
  ![Django](https://img.shields.io/badge/Django-5.2-green?logo=django)
  ![Claude](https://img.shields.io/badge/AI-Claude%20Sonnet%204.6-purple?logo=anthropic)
  ![Deploy](https://img.shields.io/badge/Deployed-Railway-purple?logo=railway)
  ![PWA](https://img.shields.io/badge/PWA-Installable-orange?logo=pwa)

  **🌐 Live at [gymprogrm.org](https://gymprogrm.org)**

</div>

---

## What is GYMprogrm?

GYMprogrm is a full-stack web application I built from scratch to run my personal training business. It replaces spreadsheets, WhatsApp voice memos, and paper programs with a single tool that handles everything — client profiles, AI-generated workout programs, blood test analysis, workout logging, billing, and a client-facing mobile portal.

The core idea: **the AI does the heavy analytical work** (reading blood tests, generating tailored programs, writing exercise descriptions) so I can focus on coaching. Every AI output passes through me before clients see it — I review, adjust, and confirm.

The app has three sides:
- **Trainer dashboard** — only I can access this (password-protected). I manage all clients, generate programs, review AI analysis, and track payments.
- **Client portal** — each client gets their own account via invite link or Google login. They see their program, log workouts, track progress, and pay — all from their phone.
- **Independent Member portal** — anyone can self-register at `/members/register/` with no invite needed. They go through a 3-step onboarding, then get access to AI Coach Alex, an AI-generated workout program, a nutrition log, posture analysis, and a progress tracker — all without a human trainer involved.

---

## Screenshots

### Trainer Dashboard — Student List
![Student List](docs/screenshots/student_list.png)

### Student Profile — Blood Test Analysis
![Blood Analysis](docs/screenshots/blood_analysis.png)

### AI Program Generation
![Program Generation](docs/screenshots/program_generate.png)

### Program Detail — AI Analysis & Workout Days
![Program Detail](docs/screenshots/program_detail.png)

### Exercise Library
![Exercise Library](docs/screenshots/exercise_library.png)

### Client Login — Mobile View
![Client Portal](docs/screenshots/client_portal.png)

### AI Coach Alex — Conversation
![AI Coach Chat](docs/screenshots/member_chat.png)

### Independent Member — Program with Exercise GIFs
![Member Program](docs/screenshots/member_program.png)

### Nutrition Log — Daily Targets & Macros
![Nutrition Log](docs/screenshots/member_nutrition.png)

---

## How the app works — end to end

### 1. Adding a client

I can add a client in two ways:

**Invite by email** — I type their email, the app generates a unique token, and Resend sends them a link like `gymprogrm.org/invite/<token>`. They click it, create an account (email/password or Google), and fill out an intake form: goals, health issues, injuries, training availability. The submission lands in my dashboard as a "Pending" application. I review it and click Accept — they become an active client.

**Manual create** — I fill in their profile directly (useful for existing clients I'm migrating over).

### 2. Generating a workout program

Once a client is active I click "Generate Program with AI". The app sends a structured prompt to **Claude Sonnet 4.6** containing:
- Name, age, gender
- Goals (e.g. "bigger glutes, lose fat")
- Health issues and injuries
- Training days per week
- Blood test analysis results (if uploaded)
- Body photo analysis (if uploaded)

Claude responds with a complete JSON structure: program name, N training days, each day with 6 exercises (muscle group, sets, reps, rest time, coaching notes), plus a full nutrition plan (daily calories, macros, 4 meals, supplement stack, fasting recommendation).

The app parses the JSON, saves everything to the database, and presents me with a review screen — I can confirm or skip each exercise before it goes live to the client. This means no AI mistake can reach a client without my approval.

### 3. Blood test analysis

The client uploads a PDF or photo of their blood test. The app sends it to **Claude Sonnet 4.6** using vision (for images) or text extraction (for PDFs). Claude:
- Identifies every abnormal marker (high/low)
- Flags urgent values that need medical attention
- Writes personalized exercise modifications (e.g. "avoid heavy compound lifts — ferritin critically low")
- Writes nutrition adjustments based on deficiencies
- Summarizes key findings in plain language

The analysis is cached in the database so it doesn't need to re-run on every page load. Key findings are automatically written to the client's health issues field so they're included in future program generation.

### 4. Exercise library

I have a library of exercises organized by muscle group. For each exercise I can generate:
- An **AI illustration** (DALL-E 3) showing proper form
- **Posture tips** written by Claude Haiku (faster and cheaper for short text tasks)

I can add any exercise from the library to any day of any program in one click.

### 5. Client portal

Clients log in at `gymprogrm.org/portal/`. They see:

- **Dashboard** — greeting, program progress bar, this week's workout count, a prominent Pay Now card if payment is due
- **Program** — their current program broken down by day, each exercise with photo, sets/reps/rest, and technique notes
- **Log workout** — tap to start a session, enter actual weights and reps, built-in rest timer between sets; previous session values are pre-filled as reference
- **History** — full log of every past workout with per-exercise breakdown
- **Tips** — trainer's personal recommendations (visible only after I confirm them) + specialist doctor referrals
- **Billing** — subscription details, amount due, next payment date, and a direct "Pay via Venmo/PayPal/Zelle" button that opens my payment link

The portal works as a **PWA (Progressive Web App)** — clients can install it on their iPhone or Android home screen and it opens fullscreen like a native app, with no browser address bar.

### 6. Billing & payment reminders

I set each client's plan (Monthly / 3 Months), amount in USD, start date, and payment method. The app calculates the next due date automatically.

A **daily cron job** on Railway runs `python manage.py send_payment_reminders` every morning at 9 AM UTC. It checks every active client and sends an email via Resend if:
- Payment is due in exactly 3 days → "Your payment is due in 3 days"
- Payment is due today → "Your payment is due today"
- Payment was due yesterday → "Your payment is overdue"

Each email is sent at most once per day per client (tracked with a `payment_reminder_sent_date` field). On my dashboard, clients show colored badges: green "Paid", yellow "Due in Xd", red "Overdue".

### 7. Multilingual support

The entire interface is translated into 10 languages: English, Russian, Spanish, French, German, Italian, Portuguese, Chinese, Arabic, Japanese. Clients pick their language from a dropdown in the header — it persists across sessions. Program names and day names are stored in both English and Russian so they display correctly regardless of language choice.

### 8. Independent Member — self-serve AI coaching

Anyone can sign up at `gymprogrm.org/members/register/` without an invite or a trainer. The flow:

**Step 1 — Goals & activity level.** The member picks their primary goal (fat loss, muscle gain, body recomposition, athletic performance, etc.) and self-reported activity level. These drive every downstream AI decision.

**Step 2 — Physical stats.** Height, weight, age, gender, and any injuries or health notes. The app calculates daily calorie and macro targets using the Mifflin-St Jeor equation adjusted for the chosen goal.

**Step 3 — Medical documents.** The member optionally uploads a doctor prescription and/or blood test results. When a blood test is uploaded, Claude Sonnet 4.6 reads it the same way it does for trainer-managed clients. These documents are stored and automatically included whenever the AI generates or updates a program.

**AI Coach Alex.** After onboarding, members get access to a conversational AI coach named Alex — a single integrated professional combining the knowledge of a personal trainer, nutritionist, and sports doctor. Alex does more than answer questions:

- When the member describes what they ate, Alex automatically logs it to the Nutrition Log (triggered by a `NUTRITION_LOG` signal detected in the response). No separate form needed.
- When the member asks for a program, Alex generates a complete, database-backed workout program (triggered by a `CREATE_PROGRAM` signal). The program appears immediately in the Program tab.
- Conversations support full message management: individual messages can be edited or deleted, and conversations can be bulk-selected and deleted.

**Program generation.** When a program is generated — whether directly from the coach or from the program page — Claude acts simultaneously as PT, nutritionist, sports doctor, and physiotherapist. The prompt includes the member's uploaded blood test and doctor prescription. Claude:
- Considers cortisol response and hormonal risk markers from the blood test
- Flags contraindicated exercises based on the prescription and lab values
- Identifies which muscle groups to grow, which to maintain/control, and which to avoid — mapped to the member's specific aesthetic or performance goal
- Sources real exercise GIFs from gymvisual.com with a consistent dark-background style so the visual presentation is professional and uniform

**Nutrition Log.** A dedicated tab shows today's calorie and macro progress against the calculated targets, with per-macro progress bars. Members can add food entries manually or let Alex log automatically from conversation. Past entries appear with an "Add again today" shortcut, and a 7-day calorie history chart visualizes the week at a glance.

**Posture Analysis.** The member uploads a standing photo. Claude Sonnet 4.6 analyses posture, flags alignment concerns (e.g. anterior pelvic tilt, uneven shoulders), and recommends corrective exercises.

**Progress page.** Shows weekly exercise count, a 14-day calorie chart, and a summary of the blood test analysis findings — so the member can see how their training, nutrition, and health markers fit together over time.

**Bottom navigation.** Five tabs: Home · Program · Alex (Coach) · Nutrition · Progress.

---

## Features

### Trainer side
- Client profiles with photo, goals, health issues, measurements, blood test, notes
- Intake form + invite-by-email workflow
- AI program generation (Claude Sonnet 4.6) — full program + nutrition plan
- Blood test AI analysis (Claude Sonnet 4.6 vision)
- Exercise library with AI illustrations (DALL-E 3) and posture tips (Claude Haiku)
- Per-student billing: plan, amount, method, status, start date
- Automatic payment reminder emails (Railway cron + Resend)
- Payment badges in student list (Paid / Due soon / Overdue)
- Trainer-written recommendations confirmed before clients see them
- Doctor/specialist referral cards on client portals

### Client side
- PWA — installable on iPhone and Android, fullscreen, no app store
- Bottom tab navigation: Home · Program · History · Tips · Billing
- Google OAuth + email/password login + forgot password flow
- Workout logging with pre-filled previous values and rest timer
- Body measurement tracking over time
- Prominent Pay Now banner when payment is due (shows exact amount)
- Direct payment links (Venmo / PayPal / Zelle)
- 10-language interface

### Independent Member side
- Self-registration at `/members/register/` — no invite, no trainer required
- 3-step onboarding: goals & activity level → physical stats → medical document upload (prescription + blood test)
- Daily calorie and macro targets calculated from profile (Mifflin-St Jeor + goal adjustment)
- AI Coach Alex — conversational coaching integrating PT, nutritionist, and sports doctor knowledge
  - Automatic nutrition logging from natural conversation (`NUTRITION_LOG` signal)
  - Automatic full program generation from conversation (`CREATE_PROGRAM` signal)
  - Message edit and delete; bulk conversation delete
- AI program generation reads uploaded blood test and doctor prescription
  - Cortisol response and hormonal risk considered
  - Contraindicated exercises identified and excluded
  - Muscle groups categorized as GROW / CONTROL / AVOID per the member's aesthetic goal
  - Real animated GIF demos from gymvisual.com (consistent dark-background style) for every exercise
- Nutrition Log: daily macro progress bars, 7-day calorie chart, "Add again today" shortcut from history
- Posture Analysis: photo upload → AI flags alignment issues and recommends corrective exercises
- Progress page: weekly exercise count, 14-day calorie chart, blood test analysis summary
- Bottom tab navigation: Home · Program · Alex (Coach) · Nutrition · Progress

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Django 5.2 + Python 3.11 | Mature, batteries-included, great ORM, fast to build with |
| Database | PostgreSQL (prod) / SQLite (dev) | Relational data fits naturally; Railway provides managed Postgres |
| AI — programs & blood analysis | Anthropic Claude Sonnet 4.6 | Best reasoning for complex, multi-step analysis tasks |
| AI — integrated coaching | Anthropic Claude Sonnet 4.6 | Powers AI Coach Alex — conversational PT + nutritionist + sports doctor with signal detection |
| AI — short text (posture tips) | Anthropic Claude Haiku 4.5 | 10× cheaper than Sonnet for simple generation tasks |
| AI — exercise illustrations | OpenAI DALL-E 3 | Best image generation for realistic exercise form photos |
| Auth | Django built-in + django-allauth | Google OAuth, email login, password reset — all in one library |
| Media storage | Cloudinary | Photos and files persist across Railway deploys (ephemeral disk) |
| Email | Resend | Reliable transactional email, verified custom domain, simple API |
| Static files | WhiteNoise | Serves CSS/JS directly from Django — no separate CDN needed |
| PWA | Web App Manifest + Service Worker | Makes the portal installable and partially offline-capable |
| Server | Gunicorn | Standard Python WSGI server |
| Deployment | Railway | Simple GitHub-connected deploys, managed Postgres, cron jobs |

---

## Services used and costs

### Monthly running costs

| Service | Plan | Cost/month | What it does |
|---|---|---|---|
| **Railway** | Hobby | **$5** | Hosts the Django app + PostgreSQL database. Auto-deploys from GitHub on every push. Also runs the daily payment reminder cron job. |
| **Anthropic Claude API** | Pay-per-use | **~$2–8** | Powers program generation (Sonnet 4.6) and blood test analysis (Sonnet 4.6). Haiku 4.5 for posture tips. Cost scales with usage — generating one full program uses ~$0.05–0.15 worth of tokens. |
| **OpenAI API** | Pay-per-use | **~$0–2** | DALL-E 3 for exercise illustrations. $0.04 per image (standard quality). One-time generation per exercise — once created, stored and reused. |
| **Cloudinary** | Free tier | **$0** | Stores client photos and blood test files. Free tier gives 25 GB storage + 25 GB bandwidth/month — more than enough for a personal trainer business. |
| **Resend** | Free tier | **$0** | Sends invite emails, password resets, and payment reminders. Free tier allows 3,000 emails/month (100/day). |
| **Google OAuth** | Free | **$0** | Google Cloud project for Google Sign-In. Free for low-volume apps (well within free tier limits). |
| **Domain (gymprogrm.org)** | Annual | **~$1.25** | ~$15/year depending on registrar. |
| **Total** | | **~$8–16/month** | |

### One-time / development costs

| Item | Cost | Notes |
|---|---|---|
| Development | Built using **Claude Code** (AI coding assistant) | No freelancer or agency cost — built solo with AI assistance |
| Claude Code subscription | $20–100/month (during development) | Anthropic's Claude Pro/Max plan used to build the app |
| Domain registration | ~$15 | One-time purchase |

> **Bottom line:** The app runs for about **$8–16/month** total. For a trainer with 10–20 paying clients, this is effectively free relative to revenue. The only cost that scales with usage is the Claude API — and even generating a program for every new client every month stays well under $10/month.

### Claude API pricing (as of 2025)

| Model | Input | Output | Used for |
|---|---|---|---|
| Claude Sonnet 4.6 | $3 / 1M tokens | $15 / 1M tokens | Program generation, blood analysis |
| Claude Haiku 4.5 | $0.80 / 1M tokens | $4 / 1M tokens | Posture tips, short descriptions |

A full program generation (sending the student profile + getting back a complete JSON program) uses roughly 3,000–8,000 tokens total = **$0.05–0.15 per program**. Blood test analysis is similar.

### OpenAI DALL-E 3 pricing

| Quality | Size | Cost per image |
|---|---|---|
| Standard | 1024×1024 | $0.04 |
| HD | 1024×1024 | $0.08 |

Exercise illustrations are generated once and cached — so the total OpenAI cost for building the full exercise library was approximately **$2–5 one-time**.

---

## Architecture decisions

**Why Django and not FastAPI or Node.js?**
Django includes everything out of the box: ORM, admin panel, migrations, auth, form validation, sessions, i18n. For a data-heavy CRUD app with complex models, Django's ORM and admin saved weeks of work. FastAPI is better for pure APIs — Django made more sense here because the frontend is server-rendered templates, not a separate SPA.

**Why server-rendered templates and not React?**
The app uses Django templates with a CSS-only design system. This means zero JavaScript build tooling, fast page loads, and full SEO. A few interactive pieces (workout logger timer, exercise confirm/skip flow) use vanilla JS inline. The PWA wraps the whole thing to feel native on mobile.

**Why PostgreSQL?**
Relational data: students have programs, programs have days, days have exercises, exercises have logs. These relationships are straightforward in a relational database and would be awkward in a document store. Railway provides managed Postgres with automatic backups.

**Why Cloudinary for media?**
Railway's filesystem is ephemeral — files written to disk disappear on redeploy. Cloudinary gives persistent storage for photos and blood test uploads with a free tier that's sufficient for a solo trainer.

**Why Resend for email?**
Simple REST API, verified custom domain (gymprogrm.org), excellent deliverability, and a free tier that covers all email needs. Django's built-in email backend connects to Resend's SMTP endpoint with no extra libraries.

**Why not a native iOS/Android app?**
A PWA was the right tradeoff: clients install it from the browser in 10 seconds, it works on any device, and I maintain one codebase. The experience (fullscreen, home screen icon, offline caching) is 90% of what a native app provides at 0% of the App Store maintenance cost.

---

## Project structure

```
GYMprogrm/
├── students/          # Profiles, intake form, invite system, blood analysis, billing
│   ├── models.py      # Student, TrainerPaymentSettings, DoctorProfile
│   ├── views.py       # All trainer + student portal views
│   ├── forms.py       # StudentForm, DoctorProfileForm
│   └── management/
│       └── commands/
│           └── send_payment_reminders.py  # Daily cron command
├── programs/          # Programs, exercise library, AI generation
│   ├── models.py      # WorkoutProgram, ProgramDay, ProgramExercise, ExerciseLibrary
│   ├── views.py       # Program CRUD + AI generation endpoint
│   └── ai.py          # All Claude/OpenAI calls (program gen, blood analysis, illustrations)
├── members/           # Independent member registration, onboarding, AI coach, nutrition, posture, progress
│   ├── models.py      # Member, MemberProgram, Conversation, Message, NutritionLog, PostureAnalysis
│   ├── views.py       # Registration, onboarding steps, coach chat, nutrition log, posture, progress
│   ├── forms.py       # OnboardingForms (goals, stats, documents)
│   └── ai.py          # Alex coach logic, signal detection (NUTRITION_LOG, CREATE_PROGRAM), program gen
├── progress/          # Workout logs per session
│   └── models.py      # WorkoutLog, ExerciseLog
├── measurements/      # Body measurements over time
│   └── models.py      # BodyMeasurement
├── gymprogrm/         # Django project config
│   ├── settings.py    # All settings + env var loading
│   └── urls.py        # Root URL routing
├── templates/
│   ├── base.html      # Base layout — trainer nav OR student bottom tab bar
│   ├── students/      # Student portal pages + trainer billing pages
│   ├── programs/      # Program detail, exercise library
│   └── members/       # Member onboarding, coach chat, nutrition log, posture, progress
├── static/
│   ├── css/base.css   # Global design system + responsive + bottom nav
│   ├── images/        # Logo, exercise illustrations
│   └── manifest.json  # PWA manifest
├── locale/            # Django i18n .po/.mo files (10 languages)
├── Procfile           # gunicorn gymprogrm.wsgi
└── railway.json       # Railway build + start commands
```

---

## Data model

```
Student
  ├── payment_plan, payment_amount, payment_start_date
  ├── payment_method, payment_handle, payment_status
  ├── WorkoutProgram (FK)
  │     └── ProgramDay (FK)
  │           └── ProgramExercise (FK) ── ExerciseLibrary
  ├── WorkoutLog (FK)
  │     └── ExerciseLog (FK)
  └── BodyMeasurement (FK)

TrainerPaymentSettings   # singleton — trainer's global Venmo/PayPal/Zelle handles
DoctorProfile            # specialist referral cards shown on client portal

Member                   # independent member (self-registered, no trainer)
  ├── goal, activity_level, height, weight, age, gender
  ├── daily_calories, protein_target, carb_target, fat_target  # calculated on onboarding
  ├── doctor_prescription (file), blood_test (file)
  ├── MemberProgram (FK)
  │     └── MemberProgramDay (FK)
  │           └── MemberProgramExercise (FK)  # includes gif_url from gymvisual.com
  ├── Conversation (FK)
  │     └── Message (FK)   # role (user/assistant), editable, deletable
  ├── NutritionLog (FK)    # date, food_name, calories, protein, carbs, fat
  └── PostureAnalysis (FK) # photo upload, AI analysis text, recommended exercises
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

Visit `http://localhost:8000` — log in as the superuser (trainer account).

Students access their portal at `http://localhost:8000/portal/`.

Independent members register at `http://localhost:8000/members/register/`.

---

## Environment variables

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=                       # leave blank → uses SQLite locally
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=               # https://gymprogrm.org

ANTHROPIC_API_KEY=                  # required — program generation, blood analysis & AI Coach Alex
OPENAI_API_KEY=                     # required — exercise illustrations (DALL-E 3)

CLOUDINARY_URL=                     # optional — persistent media on Railway
RESEND_API_KEY=                     # optional — transactional email

GOOGLE_CLIENT_ID=                   # optional — Google OAuth login
GOOGLE_CLIENT_SECRET=               # optional — Google OAuth login
```

---

## Deployment (Railway)

The app is deployed at **[gymprogrm.org](https://gymprogrm.org)** on Railway.

Every push to `main` triggers an automatic deploy:

```
✓ pip install -r requirements.txt
✓ python manage.py collectstatic --noinput
✓ python manage.py migrate --noinput
✓ gunicorn gymprogrm.wsgi
```

**Payment reminder cron job** — configured in Railway as a separate cron service:
```
Schedule: 0 9 * * *   (daily at 9 AM UTC)
Command:  python manage.py send_payment_reminders
```

---

## Installing as a mobile app

**iPhone / iOS:**
1. Open `https://gymprogrm.org/portal/` in Safari
2. Tap the Share button → "Add to Home Screen"
3. Tap Add — launches fullscreen like a native app

**Android:**
1. Open `https://gymprogrm.org/portal/` in Chrome
2. Tap ⋮ menu → "Install App"

---

## License

Private project. All rights reserved.
