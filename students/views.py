import os
import uuid
from datetime import date, datetime
from functools import wraps

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Student
from .forms import StudentForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_file_url(file_field):
    """Return a working URL for a FileField/ImageField, or None if not accessible."""
    if not file_field:
        return None
    try:
        url = file_field.url
        # Local /media/ URLs don't exist on Railway — treat as missing
        if url and url.startswith('/media/'):
            return None
        if url and 'cloudinary.com' in url and 'image/upload' in url:
            _, ext = os.path.splitext(file_field.name or '')
            if ext.lower() not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
                url = url.replace('/image/upload/', '/raw/upload/')
        return url
    except Exception:
        return None


def student_required(view_func):
    """Decorator: user must be logged-in and have a student profile."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        if not hasattr(request.user, 'student'):
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped


def get_reminders(student):
    """Return a list of reminder dicts for a student (computed at request time)."""
    reminders = []
    today = date.today()

    # Program change reminder
    active_program = student.programs.filter(is_active=True).first()
    if active_program and active_program.start_date:
        days_since = (today - active_program.start_date).days
        threshold = active_program.duration_weeks * 7
        if days_since >= threshold:
            reminders.append({
                'type': 'change_program',
                'student': student,
                'program': active_program,
                'days_since': days_since,
            })

    # Payment reminder
    if student.payment_start_date:
        days_since_payment = (today - student.payment_start_date).days
        threshold = 84 if student.payment_plan == '3months' else 28
        if days_since_payment >= threshold:
            reminders.append({
                'type': 'payment_due',
                'student': student,
                'plan': student.get_payment_plan_display(),
            })

    return reminders


# ---------------------------------------------------------------------------
# Trainer views
# ---------------------------------------------------------------------------

@login_required
def student_list(request):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    students = Student.objects.filter(is_active=True, intake_status='active')
    pending = Student.objects.filter(intake_status='pending')

    # Gather all reminders for trainer dashboard
    all_reminders = []
    for s in students:
        all_reminders.extend(get_reminders(s))

    return render(request, 'students/student_list.html', {
        'students': students,
        'pending': pending,
        'all_reminders': all_reminders,
    })


@login_required
def student_detail(request, pk):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    student = get_object_or_404(Student, pk=pk)
    reminders = get_reminders(student)
    return render(request, 'students/student_detail.html', {
        'student': student,
        'blood_test_url': _safe_file_url(student.blood_test_file),
        'photo_url': _safe_file_url(student.photo),
        'reminders': reminders,
    })


@login_required
def student_create(request):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            return redirect('students:detail', pk=student.pk)
    else:
        form = StudentForm()
    return render(request, 'students/student_form.html', {'form': form, 'title': 'Add Student'})


@login_required
def student_edit(request, pk):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    student = get_object_or_404(Student, pk=pk)
    error = None
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            # Save non-file fields first so they always persist
            instance = form.save(commit=False)
            instance.save(update_fields=[
                f for f in form.changed_data if f not in ('blood_test_file', 'photo')
            ] if any(f not in ('blood_test_file', 'photo') for f in form.changed_data) else None)

            # Handle file fields separately so a Cloudinary failure doesn't block the rest
            if 'blood_test_file' in request.FILES:
                try:
                    instance.blood_test_file = request.FILES['blood_test_file']
                    instance.save(update_fields=['blood_test_file'])
                except Exception as e:
                    error = f'Could not save blood test file: {e}'

            if 'photo' in request.FILES:
                try:
                    instance.photo = request.FILES['photo']
                    instance.save(update_fields=['photo'])
                except Exception as e:
                    if not error:
                        error = f'Could not save photo: {e}'

            if not error:
                return redirect('students:detail', pk=student.pk)
            student = instance
        # fall through to render with form errors or file error
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/student_form.html', {
        'form': form,
        'title': 'Edit Student',
        'student': student,
        'blood_test_url': _safe_file_url(student.blood_test_file),
        'photo_url': _safe_file_url(student.photo),
        'error': error,
    })


@login_required
def student_delete(request, pk):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        return redirect('students:list')
    return render(request, 'students/student_confirm_delete.html', {'student': student})


@login_required
@require_POST
def accept_intake(request, pk):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    student = get_object_or_404(Student, pk=pk)
    student.intake_status = 'active'
    student.is_active = True
    student.save(update_fields=['intake_status', 'is_active'])
    return redirect('students:detail', pk=pk)


@login_required
@require_POST
def send_invite(request, pk):
    """Generate invite token and return the invite URL."""
    if hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    student = get_object_or_404(Student, pk=pk)
    token = uuid.uuid4()
    student.invite_token = token
    student.save(update_fields=['invite_token'])
    invite_url = request.build_absolute_uri(f'/invite/{token}/')
    return JsonResponse({'url': invite_url})


# ---------------------------------------------------------------------------
# Invite registration
# ---------------------------------------------------------------------------

def invite_register(request, token):
    """Public view: student registers via invite link."""
    student = get_object_or_404(Student, invite_token=token)

    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')

        if not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm:
            error = 'Passwords do not match.'
        elif len(password) < 8:
            error = 'Password must be at least 8 characters.'
        elif User.objects.filter(username=email).exists():
            error = 'An account with this email already exists.'
        else:
            user = User.objects.create_user(username=email, email=email, password=password)
            student.user = user
            student.invite_token = None  # consume token
            if not student.email:
                student.email = email
            student.save(update_fields=['user', 'invite_token', 'email'])
            login(request, user)
            return redirect('students:portal_intake')

    return render(request, 'students/invite_register.html', {'student': student, 'error': error})


# ---------------------------------------------------------------------------
# Send intake form by email
# ---------------------------------------------------------------------------

@login_required
@require_POST
def send_intake_email(request):
    """Trainer enters an email → creates student, generates invite token, emails the invite link."""
    import httpx
    from django.conf import settings as django_settings

    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({'error': 'Email is required.'}, status=400)

    api_key = getattr(django_settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
    if not api_key:
        return JsonResponse({'error': 'Email service not configured.'}, status=500)

    # Find or create student by email
    student = Student.objects.filter(email=email).first()
    if not student:
        student = Student.objects.create(email=email, name=email, intake_status='pending', is_active=False)

    # Generate invite token
    token = uuid.uuid4()
    student.invite_token = token
    student.save(update_fields=['invite_token'])

    invite_url = request.build_absolute_uri(f'/invite/{token}/')
    body = (
        f'Hi!\n\n'
        f'Your personal trainer has invited you to create your account on GYMprogrm.\n\n'
        f'Click the link below to get started — it only takes a few minutes:\n{invite_url}\n\n'
        f'You\'ll set up your password and fill in a short intake form so your trainer can build a program tailored just for you.\n\n'
        f'— GYMprogrm'
    )

    try:
        resp = httpx.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'from': 'GYMprogrm <noreply@gymprogrm.org>',
                'to': [email],
                'subject': 'Your trainer invited you to GYMprogrm',
                'text': body,
            },
            timeout=15,
        )
        resp.raise_for_status()
        print(f'[invite email] sent to {email}', flush=True)
        return JsonResponse({'ok': True})
    except Exception as exc:
        print(f'[invite email] FAILED: {exc}', flush=True)
        # Return invite URL so trainer can copy and send manually
        return JsonResponse({'error': str(exc), 'invite_url': invite_url}, status=500)


# ---------------------------------------------------------------------------
# Public intake form
# ---------------------------------------------------------------------------

def client_intake(request):
    """Public intake form — no login required."""
    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            error = 'Please enter your name.'
        else:
            dob_raw = request.POST.get('date_of_birth', '').strip()
            dob = None
            if dob_raw:
                try:
                    dob = datetime.strptime(dob_raw, '%Y-%m-%d').date()
                except ValueError:
                    pass

            height_raw = request.POST.get('height_cm', '').strip()
            weight_raw = request.POST.get('weight_kg', '').strip()
            days_raw = request.POST.get('training_days_per_week', '').strip()
            goals = request.POST.get('goals', '').strip()
            expectations = request.POST.get('expectations', '').strip()
            if expectations:
                goals = goals + ('\n\n' if goals else '') + 'Expectations from trainer:\n' + expectations

            student = Student(
                name=name,
                gender=request.POST.get('gender', ''),
                email=request.POST.get('email', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                date_of_birth=dob,
                health_issues=request.POST.get('health_issues', '').strip(),
                goals=goals,
                training_days_per_week=int(days_raw) if days_raw.isdigit() else None,
                follow_nutrition=request.POST.get('follow_nutrition') == '1',
                height_cm=height_raw if height_raw else None,
                weight_kg=weight_raw if weight_raw else None,
                intake_status='pending',
                is_active=False,
            )
            student.save()

            file_error = None
            if request.FILES.get('blood_test_file'):
                try:
                    student.blood_test_file = request.FILES['blood_test_file']
                    student.save(update_fields=['blood_test_file'])
                except Exception as e:
                    file_error = f'Could not save blood test file: {e}'

            if request.FILES.get('photo'):
                try:
                    student.photo = request.FILES['photo']
                    student.save(update_fields=['photo'])
                except Exception as e:
                    if not file_error:
                        file_error = f'Could not save photo: {e}'

            if file_error:
                return render(request, 'students/intake_form.html', {'student': student, 'error': file_error})

            # Notify trainer via Resend API
            try:
                import httpx
                from django.conf import settings as django_settings
                api_key = getattr(django_settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
                trainer_emails = list(
                    User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True)
                )
                if api_key and trainer_emails:
                    httpx.post(
                        'https://api.resend.com/emails',
                        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                        json={
                            'from': 'GYMprogrm <noreply@gymprogrm.org>',
                            'to': trainer_emails,
                            'subject': f'New intake form: {student.name}',
                            'text': f'A new client submitted their intake form.\n\nName: {student.name}\nEmail: {student.email or "—"}\nGoals: {student.goals or "—"}\n\nView: https://gymprogrm.org/students/',
                        },
                        timeout=10,
                    )
            except Exception:
                pass

            return redirect('intake_success')

    return render(request, 'students/intake_form.html', {'error': error})


def intake_success(request):
    return render(request, 'students/intake_success.html')


# ---------------------------------------------------------------------------
# Login redirect
# ---------------------------------------------------------------------------

@login_required
def auth_redirect(request):
    """Role-based redirect after login."""
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    return redirect('students:list')


# ---------------------------------------------------------------------------
# Student portal — intake form
# ---------------------------------------------------------------------------

@student_required
def portal_intake(request):
    """Student fills in their intake form after registering."""
    student = request.user.student
    error = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            error = 'Please enter your name.'
        else:
            dob_raw = request.POST.get('date_of_birth', '').strip()
            dob = None
            if dob_raw:
                try:
                    dob = datetime.strptime(dob_raw, '%Y-%m-%d').date()
                except ValueError:
                    pass

            goals = request.POST.get('goals', '').strip()
            expectations = request.POST.get('expectations', '').strip()
            if expectations:
                goals = goals + ('\n\nExpectations from trainer:\n' if goals else 'Expectations from trainer:\n') + expectations

            height_raw = request.POST.get('height_cm', '').strip()
            weight_raw = request.POST.get('weight_kg', '').strip()
            days_raw = request.POST.get('training_days_per_week', '').strip()

            student.name = name
            student.gender = request.POST.get('gender', '')
            student.phone = request.POST.get('phone', '').strip()
            student.date_of_birth = dob
            student.health_issues = request.POST.get('health_issues', '').strip()
            student.goals = goals
            student.training_days_per_week = int(days_raw) if days_raw.isdigit() else None
            student.follow_nutrition = request.POST.get('follow_nutrition') == '1'
            student.height_cm = height_raw or None
            student.weight_kg = weight_raw or None
            student.intake_status = 'pending'
            student.save()

            file_error = None
            if request.FILES.get('blood_test_file'):
                try:
                    student.blood_test_file = request.FILES['blood_test_file']
                    student.save(update_fields=['blood_test_file'])
                except Exception as e:
                    file_error = f'Could not save blood test file: {e}'

            if request.FILES.get('photo'):
                try:
                    student.photo = request.FILES['photo']
                    student.save(update_fields=['photo'])
                except Exception as e:
                    if not file_error:
                        file_error = f'Could not save photo: {e}'

            if file_error:
                return render(request, 'students/portal_intake.html', {'student': student, 'error': file_error})

            # Notify trainer via Resend
            try:
                import httpx
                from django.conf import settings as django_settings
                api_key = getattr(django_settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
                trainer_emails = list(
                    User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True)
                )
                if api_key and trainer_emails:
                    httpx.post(
                        'https://api.resend.com/emails',
                        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                        json={
                            'from': 'GYMprogrm <noreply@gymprogrm.org>',
                            'to': trainer_emails,
                            'subject': f'New intake form submitted: {student.name}',
                            'text': (
                                f'Your client {student.name} has submitted their intake form.\n\n'
                                f'Email: {student.email or "—"}\n'
                                f'Goals: {student.goals or "—"}\n\n'
                                f'Review and generate their program:\n'
                                f'https://gymprogrm.org/students/{student.pk}/'
                            ),
                        },
                        timeout=10,
                    )
            except Exception:
                pass

            return redirect('students:portal_dashboard')

    return render(request, 'students/portal_intake.html', {'student': student, 'error': error})


# ---------------------------------------------------------------------------
# Student portal views
# ---------------------------------------------------------------------------

@student_required
def portal_dashboard(request):
    from datetime import date as _date
    student = request.user.student
    if student.intake_status == 'pending':
        return redirect('students:portal_intake')
    reminders = get_reminders(student)
    active_program = student.programs.filter(is_active=True).prefetch_related('days').first()

    days_remaining = None
    if active_program and active_program.start_date:
        elapsed = (_date.today() - active_program.start_date).days
        total = active_program.duration_weeks * 7
        days_remaining = max(0, total - elapsed)
        progress_pct = min(100, int(elapsed / total * 100)) if total else 0
    else:
        progress_pct = 0

    recent_logs = student.workout_logs.select_related('program_day').order_by('-date')[:5]

    # Workouts this week
    from datetime import timedelta
    week_start = _date.today() - timedelta(days=_date.today().weekday())
    workouts_this_week = student.workout_logs.filter(date__gte=week_start).count()

    # Next workout day (first day of active program)
    next_day = None
    if active_program:
        next_day = active_program.days.first()

    # Active doctors
    from .models import DoctorProfile
    doctors = DoctorProfile.objects.filter(is_active=True)

    return render(request, 'students/student_portal_dashboard.html', {
        'student': student,
        'active_program': active_program,
        'days_remaining': days_remaining,
        'progress_pct': progress_pct,
        'reminders': reminders,
        'recent_logs': recent_logs,
        'workouts_this_week': workouts_this_week,
        'next_day': next_day,
        'doctors': doctors,
        'photo_url': _safe_file_url(student.photo),
        'blood_test_url': _safe_file_url(student.blood_test_file),
    })


@student_required
def portal_program(request):
    from progress.models import ExerciseLog
    student = request.user.student
    active_program = student.programs.filter(is_active=True).prefetch_related(
        'days__exercises__exercise'
    ).first()

    # Last logged weight/reps per program exercise so we can show "last session" on the page
    last_weights = {}
    if active_program:
        for day in active_program.days.all():
            for ex in day.exercises.filter(confirmed=True):
                last_log = ExerciseLog.objects.filter(
                    workout_log__student=student,
                    program_exercise=ex,
                ).order_by('-workout_log__date').first()
                if last_log:
                    last_weights[ex.pk] = {
                        'weight': last_log.weight_kg,
                        'reps': last_log.reps_done,
                        'date': last_log.workout_log.date,
                    }

    return render(request, 'students/student_portal_program.html', {
        'student': student,
        'program': active_program,
        'last_weights': last_weights,
    })


@student_required
def portal_log_workout(request, program_day_id):
    from programs.models import ProgramDay
    from progress.models import WorkoutLog, ExerciseLog

    student = request.user.student
    program_day = get_object_or_404(ProgramDay, pk=program_day_id, program__student=student)
    exercises = program_day.exercises.select_related('exercise').order_by('order')

    error = None
    if request.method == 'POST':
        log = WorkoutLog.objects.create(
            student=student,
            program_day=program_day,
            notes=request.POST.get('notes', '').strip(),
            completed=True,
        )
        for ex in exercises:
            key = f'exercise_{ex.pk}'
            weight_raw = request.POST.get(f'{key}_weight', '').strip()
            reps_raw = request.POST.get(f'{key}_reps', '').strip()
            sets_raw = request.POST.get(f'{key}_sets', '').strip()
            ExerciseLog.objects.create(
                workout_log=log,
                program_exercise=ex,
                exercise_name=ex.exercise.name,
                sets_done=int(sets_raw) if sets_raw.isdigit() else ex.sets,
                reps_done=reps_raw or ex.reps,
                weight_kg=weight_raw if weight_raw else None,
                notes=request.POST.get(f'{key}_notes', '').strip(),
            )
        return redirect('students:portal_history')

    # Last session data per exercise for pre-filling inputs
    last_weights = {}
    for ex in exercises:
        last_log = ExerciseLog.objects.filter(
            workout_log__student=student,
            program_exercise=ex,
        ).order_by('-workout_log__date').first()
        if last_log:
            last_weights[ex.pk] = {
                'weight': last_log.weight_kg,
                'reps': last_log.reps_done,
                'date': last_log.workout_log.date,
            }

    confirmed_exercises = [ex for ex in exercises if ex.confirmed]

    return render(request, 'students/student_portal_log_workout.html', {
        'student': student,
        'program_day': program_day,
        'exercises': confirmed_exercises,
        'last_weights': last_weights,
        'total': len(confirmed_exercises),
        'error': error,
    })


@student_required
@student_required
def portal_history(request):
    from progress.models import WorkoutLog

    student = request.user.student
    logs = student.workout_logs.prefetch_related(
        'exercise_logs'
    ).select_related('program_day').order_by('-date')

    return render(request, 'students/student_portal_history.html', {
        'student': student,
        'logs': logs,
    })


# ---------------------------------------------------------------------------
# Blood analysis (trainer only)
# ---------------------------------------------------------------------------

def _health_issues_from_analysis(analysis):
    lines = []
    for d in analysis.get('deficiencies', []):
        severity_map = {'severe': 'тяжёлый', 'moderate': 'умеренный', 'mild': 'лёгкий'}
        sev = severity_map.get(d.get('severity', ''), d.get('severity', ''))
        line = f"• Дефицит: {d['nutrient']}"
        if sev:
            line += f" ({sev})"
        if d.get('impact_on_training'):
            line += f" — {d['impact_on_training']}"
        lines.append(line)

    deficiency_names = {d['nutrient'].lower() for d in analysis.get('deficiencies', [])}
    for m in analysis.get('markers', []):
        if m.get('status') not in ('low', 'high', 'critical_low', 'critical_high'):
            continue
        if m['name'].lower() in deficiency_names:
            continue
        status_map = {
            'low': 'снижен', 'high': 'повышен',
            'critical_low': 'критически снижен', 'critical_high': 'критически повышен',
        }
        status = status_map.get(m.get('status', ''), '')
        line = f"• {m['name']} {status}".strip()
        if m.get('value'):
            line += f" ({m['value']})"
        if m.get('interpretation'):
            line += f" — {m['interpretation']}"
        lines.append(line)

    for item in analysis.get('urgent_attention', []):
        lines.append(f"⚠️ {item}")

    return '\n'.join(lines)


@login_required
@require_POST
def analyze_blood(request, pk):
    import threading
    from django.db import connections

    if hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Not authorized'}, status=403)

    student = get_object_or_404(Student, pk=pk)
    if not student.blood_test_file:
        return JsonResponse({'error': 'No blood test file uploaded'}, status=400)

    Student.objects.filter(pk=pk).update(blood_analysis={'_processing': True})

    from django.utils.translation import get_language
    _lang = get_language() or 'en'

    def _run(student_pk, lang=_lang):
        try:
            from programs.ai import analyze_blood_test
            s = Student.objects.get(pk=student_pk)
            analysis = analyze_blood_test(s, language=lang)
            if analysis is None:
                Student.objects.filter(pk=student_pk).update(
                    blood_analysis={'_error': 'Could not read the blood test file.'})
                return

            blood_block = _health_issues_from_analysis(analysis)
            s.refresh_from_db()
            s.blood_analysis = analysis
            if blood_block:
                marker = '🩸 Анализ крови (AI):'
                existing = (s.health_issues or '').strip()
                if marker in existing:
                    existing = existing[:existing.index(marker)].strip()
                s.health_issues = (existing + '\n\n' if existing else '') + marker + '\n' + blood_block
            s.save(update_fields=['blood_analysis', 'health_issues'])
        except Exception as e:
            Student.objects.filter(pk=student_pk).update(blood_analysis={'_error': str(e)})
        finally:
            connections.close_all()

    t = threading.Thread(target=_run, args=(pk,), daemon=True)
    t.start()
    return JsonResponse({'status': 'processing'})


@login_required
def check_blood_analysis(request, pk):
    if hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    student = get_object_or_404(Student, pk=pk)
    if not student.blood_analysis:
        return JsonResponse({'status': 'none'})
    if student.blood_analysis.get('_processing'):
        return JsonResponse({'status': 'processing'})
    if student.blood_analysis.get('_error'):
        err = student.blood_analysis['_error']
        Student.objects.filter(pk=pk).update(blood_analysis=None)
        return JsonResponse({'status': 'error', 'error': err})
    return JsonResponse({'status': 'done'})


# ---------------------------------------------------------------------------
# Photo analysis (trainer only)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def analyze_photo(request, pk):
    import threading
    from django.db import connections

    if hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Not authorized'}, status=403)

    student = get_object_or_404(Student, pk=pk)
    if not student.photo:
        return JsonResponse({'error': 'No photo uploaded'}, status=400)

    Student.objects.filter(pk=pk).update(photo_analysis='_processing')

    def _run(student_pk):
        try:
            import anthropic
            from programs.ai import _photo_block, _analyze_photo
            s = Student.objects.get(pk=student_pk)
            client = anthropic.Anthropic()
            photo_blocks, attached = _photo_block(s)
            if not attached:
                Student.objects.filter(pk=student_pk).update(photo_analysis='_error:Could not load photo.')
                return
            analysis = _analyze_photo(client, s, photo_blocks)
            Student.objects.filter(pk=student_pk).update(photo_analysis=analysis or '_error:No result.')
        except Exception as e:
            Student.objects.filter(pk=student_pk).update(photo_analysis=f'_error:{e}')
        finally:
            connections.close_all()

    t = threading.Thread(target=_run, args=(pk,), daemon=True)
    t.start()
    return JsonResponse({'status': 'processing'})


@login_required
def check_photo_analysis(request, pk):
    if hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    student = get_object_or_404(Student, pk=pk)
    val = student.photo_analysis or ''
    if not val:
        return JsonResponse({'status': 'none'})
    if val == '_processing':
        return JsonResponse({'status': 'processing'})
    if val.startswith('_error:'):
        err = val[len('_error:'):]
        Student.objects.filter(pk=pk).update(photo_analysis='')
        return JsonResponse({'status': 'error', 'error': err})
    return JsonResponse({'status': 'done', 'analysis': val})


# ---------------------------------------------------------------------------
# AI Recommendations (student portal)
# ---------------------------------------------------------------------------

@student_required
@require_POST
def portal_get_recommendations(request):
    import threading
    from django.db import connections
    from django.utils.translation import get_language

    student = request.user.student
    Student.objects.filter(pk=student.pk).update(ai_recommendations={'_processing': True})

    _lang = get_language() or 'ru'

    def _run(student_pk, lang=_lang):
        try:
            from programs.ai import generate_student_recommendations
            s = Student.objects.get(pk=student_pk)
            result = generate_student_recommendations(s, language=lang)
            Student.objects.filter(pk=student_pk).update(ai_recommendations=result)
        except Exception as e:
            Student.objects.filter(pk=student_pk).update(ai_recommendations={'_error': str(e)})
        finally:
            connections.close_all()

    t = threading.Thread(target=_run, args=(student.pk,), daemon=True)
    t.start()
    return JsonResponse({'status': 'processing'})


@student_required
def portal_check_recommendations(request):
    student = request.user.student
    r = student.ai_recommendations
    if not r:
        return JsonResponse({'status': 'none'})
    if r.get('_processing'):
        return JsonResponse({'status': 'processing'})
    if r.get('_error'):
        Student.objects.filter(pk=student.pk).update(ai_recommendations=None)
        return JsonResponse({'status': 'error', 'error': r['_error']})
    return JsonResponse({'status': 'done'})


@student_required
def portal_recommendations(request):
    student = request.user.student
    raw = student.ai_recommendations
    recs = None
    recs_processing = False
    if raw:
        if raw.get('_processing'):
            recs_processing = True
        elif not raw.get('_error'):
            recs = raw
    return render(request, 'students/student_portal_recommendations.html', {
        'student': student,
        'recs': recs,
        'recs_processing': recs_processing,
    })


# ---------------------------------------------------------------------------
# Request new program (student portal)
# ---------------------------------------------------------------------------

@student_required
@require_POST
def portal_request_program(request):
    import httpx
    from django.conf import settings as django_settings

    student = request.user.student
    message = request.POST.get('message', '').strip() or 'I would like a new 2-week program.'

    try:
        api_key = getattr(django_settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
        trainer_emails = list(
            User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True)
        )
        if api_key and trainer_emails:
            httpx.post(
                'https://api.resend.com/emails',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'from': 'GYMprogrm <noreply@gymprogrm.org>',
                    'to': trainer_emails,
                    'subject': f'New program request: {student.name}',
                    'text': (
                        f'{student.name} has requested a new 2-week program.\n\n'
                        f'Message: {message}\n\n'
                        f'Create their program: https://gymprogrm.org/students/{student.pk}/'
                    ),
                },
                timeout=10,
            )
    except Exception:
        pass

    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# Doctor profiles (trainer admin)
# ---------------------------------------------------------------------------

@login_required
def doctor_list(request):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    from .models import DoctorProfile
    doctors = DoctorProfile.objects.all()
    return render(request, 'students/doctor_list.html', {'doctors': doctors})


@login_required
def doctor_create(request):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    from .forms import DoctorProfileForm
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('students:doctor_list')
    else:
        form = DoctorProfileForm()
    return render(request, 'students/doctor_form.html', {'form': form, 'title': 'Add Doctor'})


@login_required
def doctor_edit(request, pk):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    from .models import DoctorProfile
    from .forms import DoctorProfileForm
    doctor = get_object_or_404(DoctorProfile, pk=pk)
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            return redirect('students:doctor_list')
    else:
        form = DoctorProfileForm(instance=doctor)
    return render(request, 'students/doctor_form.html', {'form': form, 'title': 'Edit Doctor', 'doctor': doctor})


@login_required
@require_POST
def doctor_delete(request, pk):
    if hasattr(request.user, 'student'):
        return redirect('students:portal_dashboard')
    from .models import DoctorProfile
    get_object_or_404(DoctorProfile, pk=pk).delete()
    return redirect('students:doctor_list')
