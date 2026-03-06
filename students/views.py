from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Student
from .forms import StudentForm


def _safe_file_url(file_field):
    """Return a working URL for a FileField/ImageField.
    django-cloudinary-storage returns image/upload for all files, but PDFs
    need raw/upload — we patch the URL for non-image extensions."""
    if not file_field:
        return None
    try:
        import os
        url = file_field.url
        if url and 'cloudinary.com' in url and 'image/upload' in url:
            _, ext = os.path.splitext(file_field.name or '')
            if ext.lower() not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'):
                url = url.replace('/image/upload/', '/raw/upload/')
        return url
    except Exception:
        return None




@login_required
def student_list(request):
    students = Student.objects.filter(is_active=True, intake_status='active')
    pending = Student.objects.filter(intake_status='pending')
    return render(request, 'students/student_list.html', {'students': students, 'pending': pending})


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return render(request, 'students/student_detail.html', {
        'student': student,
        'blood_test_url': _safe_file_url(student.blood_test_file),
        'photo_url': _safe_file_url(student.photo),
    })


@login_required
def student_create(request):
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
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            return redirect('students:detail', pk=student.pk)
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/student_form.html', {
        'form': form,
        'title': 'Edit Student',
        'student': student,
        'blood_test_url': _safe_file_url(student.blood_test_file),
        'photo_url': _safe_file_url(student.photo),
    })


@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        return redirect('students:list')
    return render(request, 'students/student_confirm_delete.html', {'student': student})


def client_intake(request):
    """Public intake form — no login required. Clients fill this in themselves."""
    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            error = 'Пожалуйста, введите ваше имя.'
        else:
            from datetime import datetime
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

            student = Student(
                name=name,
                gender=request.POST.get('gender', ''),
                email=request.POST.get('email', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                date_of_birth=dob,
                health_issues=request.POST.get('health_issues', '').strip(),
                goals=request.POST.get('goals', '').strip(),
                training_days_per_week=int(days_raw) if days_raw.isdigit() else None,
                follow_nutrition=request.POST.get('follow_nutrition') == '1',
                height_cm=height_raw if height_raw else None,
                weight_kg=weight_raw if weight_raw else None,
                intake_status='pending',
                is_active=False,
            )
            student.save()

            if request.FILES.get('blood_test_file'):
                student.blood_test_file = request.FILES['blood_test_file']
                student.save(update_fields=['blood_test_file'])

            return redirect('intake_success')

    return render(request, 'students/intake_form.html', {'error': error})


def intake_success(request):
    return render(request, 'students/intake_success.html')


@login_required
@require_POST
def accept_intake(request, pk):
    """Trainer accepts a pending intake — activates the student."""
    student = get_object_or_404(Student, pk=pk)
    student.intake_status = 'active'
    student.is_active = True
    student.save(update_fields=['intake_status', 'is_active'])
    return redirect('students:detail', pk=pk)


def _health_issues_from_analysis(analysis):
    """
    Build a professional health issues text block from the blood analysis JSON.
    Returns a string to be appended to student.health_issues.
    """
    lines = []

    # Deficiencies — most clinically important
    for d in analysis.get('deficiencies', []):
        severity_map = {'severe': 'тяжёлый', 'moderate': 'умеренный', 'mild': 'лёгкий'}
        sev = severity_map.get(d.get('severity', ''), d.get('severity', ''))
        line = f"• Дефицит: {d['nutrient']}"
        if sev:
            line += f" ({sev})"
        if d.get('impact_on_training'):
            line += f" — {d['impact_on_training']}"
        lines.append(line)

    # Abnormal markers not already covered as a named deficiency
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

    # Urgent items
    for item in analysis.get('urgent_attention', []):
        lines.append(f"⚠️ {item}")

    return '\n'.join(lines)


@login_required
@require_POST
def analyze_blood(request, pk):
    """
    Start blood test analysis in a background thread and return immediately.
    Frontend polls /check-blood-analysis/ every 3 s until done.
    """
    import threading
    from django.db import connections

    student = get_object_or_404(Student, pk=pk)
    if not student.blood_test_file:
        return JsonResponse({'error': 'No blood test file uploaded'}, status=400)

    # Mark as processing so polling knows it started
    Student.objects.filter(pk=pk).update(blood_analysis={'_processing': True})

    def _run(student_pk):
        try:
            # Each thread needs its own DB connection
            from programs.ai import analyze_blood_test
            s = Student.objects.get(pk=student_pk)
            analysis = analyze_blood_test(s)
            if analysis is None:
                Student.objects.filter(pk=student_pk).update(
                    blood_analysis={'_error': 'Could not read the blood test file. Please re-upload it via Edit Student.'})
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
    """Poll endpoint: returns processing / done / error."""
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
