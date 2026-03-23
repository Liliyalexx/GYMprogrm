import json
import re as _re
from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import get_language


_RU_REPS_MAP = {
    r'на каждую ногу': 'each leg',
    r'на каждую сторону': 'each side',
    r'на каждую руку': 'each arm',
    r'на сторону': 'each side',
    r'на ногу': 'each leg',
    r'на руку': 'each arm',
    r'каждая сторона': 'each side',
    r'каждая нога': 'each leg',
    r'секунд': 'sec',
    r'сек': 'sec',
    r'минут': 'min',
    r'мин': 'min',
}


def _clean_reps(reps_str):
    """Strip Russian text from reps field, replacing known phrases with English."""
    s = str(reps_str)
    for ru, en in _RU_REPS_MAP.items():
        s = _re.sub(ru, en, s, flags=_re.IGNORECASE)
    # Remove any remaining Cyrillic
    s = _re.sub(r'\s*[а-яёА-ЯЁ][а-яёА-ЯЁ\s]*', '', s).strip()
    return s or reps_str

from students.models import Student
from .models import ExerciseLibrary, WorkoutProgram, ProgramDay, ProgramExercise, ProgramTemplate, ProgramTemplateDay, ProgramTemplateExercise
from .ai import suggest_program, suggest_nutrition, correct_text, generate_exercise_illustration, backfill_english_names, translate_program_section, suggest_warmup_stretch_exercises


@login_required
def program_list(request, student_pk):
    student = get_object_or_404(Student, pk=student_pk)
    programs = student.programs.all()
    return render(request, 'programs/program_list.html', {'student': student, 'programs': programs})


@login_required
@require_POST
def delete_program(request, pk):
    program = get_object_or_404(WorkoutProgram, pk=pk)
    student_pk = program.student.pk
    program.delete()
    return redirect('students:detail', pk=student_pk)


@login_required
def program_detail(request, pk):
    program = get_object_or_404(WorkoutProgram, pk=pk)
    exercise_library_qs = ExerciseLibrary.objects.all().values('pk', 'name', 'muscle_group')
    warmup_library = {ex.name.lower(): ex for ex in ExerciseLibrary.objects.filter(exercise_type='warmup')}
    stretch_library = {ex.name.lower(): ex for ex in ExerciseLibrary.objects.filter(exercise_type='stretch')}
    return render(request, 'programs/program_detail.html', {
        'program': program,
        'exercise_library': list(exercise_library_qs),
        'muscle_choices': ExerciseLibrary.MUSCLE_GROUP_CHOICES,
        'warmup_library': warmup_library,
        'stretch_library': stretch_library,
    })


@login_required
def program_generate(request, student_pk):
    """
    Step 1: Call AI to get exercise suggestions.
    Step 2: Create the WorkoutProgram + ProgramDays (unconfirmed).
    Step 3: Show React island for trainer to confirm each exercise.
    """
    student = get_object_or_404(Student, pk=student_pk)

    if request.method == 'POST' and 'generate' in request.POST:
        training_days = int(request.POST.get('training_days', 3))
        training_location = request.POST.get('training_location', 'gym')
        try:
            ai_result = suggest_program(student, training_days, training_location=training_location, language=get_language() or 'en')
        except Exception as e:
            return render(request, 'programs/program_generate.html', {
                'student': student,
                'error': str(e),
            })

        try:
            # Create program
            key_findings = ai_result.get('key_findings', [])
            program = WorkoutProgram.objects.create(
                student=student,
                name=ai_result.get('program_name', 'Программа тренировок'),
                name_en=ai_result.get('program_name_en', ''),
                description='\n'.join(key_findings) if key_findings else ai_result.get('description', ''),
                training_days=training_days,
                nutrition_plan=ai_result.get('nutrition'),
                start_date=date.today(),
            )

            exercise_library = {ex.name.lower(): ex for ex in ExerciseLibrary.objects.all()}
            suggestions = []

            MUSCLE_KEYWORDS = {
                'glute': 'glutes', 'ягодиц': 'glutes', 'butt': 'glutes',
                'leg': 'legs', 'squat': 'legs', 'lunge': 'legs', 'нога': 'legs', 'ног': 'legs',
                'back': 'back', 'row': 'back', 'pull': 'back', 'спин': 'back',
                'chest': 'chest', 'push': 'chest', 'грудь': 'chest',
                'shoulder': 'shoulders', 'плеч': 'shoulders', 'press': 'shoulders',
                'bicep': 'arms', 'tricep': 'arms', 'curl': 'arms', 'рук': 'arms',
                'core': 'core', 'plank': 'core', 'crunch': 'core', 'пресс': 'core', 'ab': 'core',
                'cardio': 'cardio', 'run': 'cardio', 'jump': 'cardio', 'кардио': 'cardio',
            }

            def _infer_muscle_group(name, day_name=''):
                text = (name + ' ' + day_name).lower()
                for kw, mg in MUSCLE_KEYWORDS.items():
                    if kw in text:
                        return mg
                return 'full_body'

            used_globally = set()  # track exercise PKs across all days
            for day_data in ai_result.get('days', []):
                day = ProgramDay.objects.create(
                    program=program,
                    day_number=day_data.get('day_number', 1),
                    name=day_data.get('day_name', 'День'),
                    name_en=day_data.get('day_name_en', ''),
                    warmup_data=day_data.get('warmup') or None,
                    cooldown_data=day_data.get('cooldown') or None,
                )
                used_in_day = set()  # track exercise PKs within this day
                for order, ex_data in enumerate(day_data.get('exercises', [])):
                    name_key = ex_data.get('name', '').lower()
                    if not name_key:
                        continue
                    library_ex = exercise_library.get(name_key)
                    if not library_ex:
                        _GENERIC = {'dumbbell', 'barbell', 'cable', 'lever', 'machine',
                                    'with', 'without', 'using', 'band', 'weight'}
                        name_words = [w for w in name_key.split() if len(w) > 3 and w not in _GENERIC]
                        best_key, best_score = None, 0
                        for key in exercise_library:
                            score = sum(1 for w in name_words if w in key)
                            if score > best_score:
                                best_score, best_key = score, key
                        if best_score >= 2:
                            library_ex = exercise_library[best_key]

                    if not library_ex and training_location == 'home':
                        mg = ex_data.get('muscle_group') or _infer_muscle_group(ex_data.get('name', ''), day_data.get('day_name', ''))
                        library_ex = ExerciseLibrary.objects.create(
                            name=ex_data['name'],
                            muscle_group=mg,
                            description=ex_data.get('reason_ru') or ex_data.get('reason') or ex_data['name'],
                            difficulty='beginner',
                        )
                        exercise_library[ex_data['name'].lower()] = library_ex

                    if library_ex:
                        if library_ex.pk in used_in_day or library_ex.pk in used_globally:
                            continue  # skip duplicate
                        used_in_day.add(library_ex.pk)
                        used_globally.add(library_ex.pk)
                        pe = ProgramExercise.objects.create(
                            program_day=day,
                            exercise=library_ex,
                            sets=ex_data.get('sets', 3),
                            reps=_clean_reps(ex_data.get('reps', '10')),
                            name_ru=ex_data.get('name_ru', ''),
                            reason_ru=ex_data.get('reason_ru', ''),
                            order=order,
                            confirmed=False,
                        )
                        suggestions.append({
                            'id': pe.pk,
                            'name': library_ex.name,
                            'name_ru': ex_data.get('name_ru', library_ex.name),
                            'muscle_group': library_ex.get_muscle_group_display(),
                            'photo_url': library_ex.photo_url,
                            'description': library_ex.description,
                            'sets': pe.sets,
                            'reps': pe.reps,
                            'reason': ex_data.get('reason', ''),
                            'reason_ru': ex_data.get('reason_ru', ''),
                            'day_name': day.name,
                        })

            return render(request, 'programs/program_generate.html', {
                'student': student,
                'program': program,
                'suggestions_json': json.dumps(suggestions),
            })

        except Exception as e:
            return render(request, 'programs/program_generate.html', {
                'student': student,
                'error': f'Ошибка при создании программы: {e}',
            })

    return render(request, 'programs/program_generate.html', {'student': student})


@login_required
@require_POST
def retranslate_section(request, pk):
    """AJAX: force re-translate a program section to English (clears existing EN translation first)."""
    program = get_object_or_404(WorkoutProgram, pk=pk)
    data = json.loads(request.body)
    section = data.get('section', '')
    if section not in ('analysis', 'nutrition'):
        return JsonResponse({'error': 'Unknown section'}, status=400)
    try:
        if section == 'analysis':
            program.description_en = ''
            program.save(update_fields=['description_en'])
        elif section == 'nutrition':
            program.nutrition_plan_en = None
            program.save(update_fields=['nutrition_plan_en'])
        translate_program_section(program, section)
        return JsonResponse({'status': 'ok'})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
@require_POST
def toggle_share_section(request, pk):
    """AJAX: toggle whether a program section is shared with the student.
    Body: {'section': 'goals'|'analysis'|'nutrition', 'enabled': true|false}
    On first enable of analysis/nutrition, triggers translation to English.
    """
    import logging
    logger = logging.getLogger(__name__)
    program = get_object_or_404(WorkoutProgram, pk=pk)
    data = json.loads(request.body)
    section = data.get('section', '')
    enabled = bool(data.get('enabled', False))

    if section not in ('goals', 'analysis', 'nutrition'):
        return JsonResponse({'error': 'Unknown section'}, status=400)

    # Translate on first enable if not already translated
    if enabled and section in ('analysis', 'nutrition'):
        try:
            translate_program_section(program, section)
            program.refresh_from_db()
        except Exception as exc:
            logger.exception('translate_program_section failed for section=%s: %s', section, exc)
            return JsonResponse({'error': str(exc)}, status=500)

    shared = program.shared_sections or {}
    shared[section] = enabled
    program.shared_sections = shared
    program.save(update_fields=['shared_sections'])
    return JsonResponse({'status': 'ok', 'section': section, 'enabled': enabled})


@login_required
@require_POST
def backfill_program_english(request, pk):
    """Translate all empty name_en fields and clean Russian reps for an existing program."""
    program = get_object_or_404(WorkoutProgram, pk=pk)
    try:
        p, d, r = backfill_english_names(program)
        from django.contrib import messages
        messages.success(request, f'Translated: {p} program name, {d} day names, {r} reps cleaned.')
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f'Translation failed: {e}')
    return redirect('programs:detail', pk=pk)


@login_required
@require_POST
def regenerate_nutrition(request, pk):
    program = get_object_or_404(WorkoutProgram, pk=pk)
    findings_summary = program.description or ''
    try:
        nutrition = suggest_nutrition(program.student, findings_summary, language=get_language() or 'en')
        program.nutrition_plan = nutrition
        program.save(update_fields=['nutrition_plan'])
    except Exception as e:
        pass  # keep existing plan if AI fails
    return redirect('programs:detail', pk=pk)


@login_required
@require_POST
def confirm_exercise(request):
    """AJAX endpoint: trainer confirms an exercise, optionally updating weight/sets/reps."""
    data = json.loads(request.body)
    pe = get_object_or_404(ProgramExercise, pk=data['id'])
    pe.confirmed = True
    pe.sets = int(data.get('sets', pe.sets))
    pe.reps = str(data.get('reps', pe.reps))
    if data.get('weight_kg'):
        pe.weight_kg = float(data['weight_kg'])
    pe.notes = data.get('notes', '')
    pe.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def skip_exercise(request):
    """AJAX endpoint: trainer skips (deletes) an unconfirmed exercise suggestion."""
    data = json.loads(request.body)
    pe = get_object_or_404(ProgramExercise, pk=data['id'])
    pe.delete()
    return JsonResponse({'status': 'ok'})


@login_required
def exercise_library(request):
    exercises = ExerciseLibrary.objects.all()
    muscle_filter = request.GET.get('muscle', '')
    type_filter = request.GET.get('type', '')  # 'main', 'warmup', 'stretch', or ''
    if muscle_filter:
        exercises = exercises.filter(muscle_group=muscle_filter)
    if type_filter:
        exercises = exercises.filter(exercise_type=type_filter)

    from students.models import Student
    students = Student.objects.filter(is_active=True).prefetch_related(
        'programs__days'
    )

    return render(request, 'programs/exercise_library.html', {
        'exercises': exercises,
        'muscle_filter': muscle_filter,
        'type_filter': type_filter,
        'muscle_choices': ExerciseLibrary.MUSCLE_GROUP_CHOICES,
        'exercise_type_choices': ExerciseLibrary.EXERCISE_TYPE_CHOICES,
        'students': students,
    })


@login_required
@require_POST
def add_exercise_to_program(request):
    exercise_pk = request.POST.get('exercise_pk')
    day_pk = request.POST.get('day_pk')
    exercise = get_object_or_404(ExerciseLibrary, pk=exercise_pk)
    day = get_object_or_404(ProgramDay, pk=day_pk)
    order = day.exercises.count()
    ProgramExercise.objects.create(
        program_day=day,
        exercise=exercise,
        sets=3,
        reps='10-12',
        order=order,
        confirmed=True,
    )
    return redirect(request.POST.get('next', 'programs:exercise_library'))


@login_required
@require_POST
def generate_illustration(request):
    import logging
    logger = logging.getLogger(__name__)
    try:
        data = json.loads(request.body)
        ex = get_object_or_404(ExerciseLibrary, pk=data['id'])
        logger.info('generate_illustration: starting for exercise pk=%s name=%r', ex.pk, ex.name)
        result = generate_exercise_illustration(ex.name, ex.get_muscle_group_display(), ex.description)
        ex.photo_url = result['image_url']
        ex.photo_url_2 = result.get('image_url_2', '')
        ex.posture_tips = result['posture_tips']
        ex.save(update_fields=['photo_url', 'photo_url_2', 'posture_tips'])
        logger.info('generate_illustration: done for pk=%s', ex.pk)
        return JsonResponse({'image_url': result['image_url'], 'image_url_2': result.get('image_url_2', ''), 'posture_tips': result['posture_tips']})
    except Exception as exc:
        logger.exception('generate_illustration failed: %s', exc)
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
def generate_missing_illustrations(request):
    """
    Returns JSON list of exercises missing photo_url so the page can queue them one by one.
    GET → list of {id, name}
    """
    qs = ExerciseLibrary.objects.filter(photo_url='').order_by('muscle_group', 'name')
    return JsonResponse({'exercises': [{'id': ex.pk, 'name': ex.name} for ex in qs]})


@login_required
@require_POST
def update_exercise_photo(request):
    data = json.loads(request.body)
    ex = get_object_or_404(ExerciseLibrary, pk=data['id'])
    ex.photo_url = data.get('photo_url', '').strip()
    ex.save(update_fields=['photo_url'])
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def upload_exercise_photo(request):
    """Upload one or two image files for an exercise. Stores to Cloudinary if configured, else saves locally."""
    from django.conf import settings as _settings
    ex_id = request.POST.get('id')
    slot = request.POST.get('slot', '1')  # '1' = start position, '2' = peak position
    ex = get_object_or_404(ExerciseLibrary, pk=ex_id)
    img = request.FILES.get('photo')
    if not img:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    try:
        if getattr(_settings, 'CLOUDINARY_URL', ''):
            import cloudinary.uploader
            result = cloudinary.uploader.upload(
                img,
                folder='gymprogrm/exercises',
                public_id=f'exercise_{ex.pk}_slot{slot}',
                overwrite=True,
                resource_type='image',
            )
            url = result['secure_url']
        else:
            # Fallback: save to MEDIA_ROOT and return relative URL (dev only)
            import os
            from django.core.files.storage import default_storage
            path = default_storage.save(f'exercises/exercise_{ex.pk}_slot{slot}{os.path.splitext(img.name)[1]}', img)
            url = default_storage.url(path)

        if slot == '2':
            ex.photo_url_2 = url
            ex.save(update_fields=['photo_url_2'])
        else:
            ex.photo_url = url
            ex.save(update_fields=['photo_url'])
        return JsonResponse({'status': 'ok', 'url': url, 'slot': slot})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
@require_POST
def create_exercise(request):
    """Create a new exercise in the library and redirect back.
    If generate_image=1, the redirect includes ?autogen=<pk> so the page
    auto-triggers the AJAX illustration via the existing generate_illustration endpoint."""
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    muscle_group = request.POST.get('muscle_group', 'full_body')
    difficulty = request.POST.get('difficulty', 'beginner')
    exercise_type = request.POST.get('exercise_type', 'main')
    if not name:
        from django.contrib import messages
        messages.error(request, 'Exercise name is required.')
        return redirect('programs:exercise_library')
    ex = ExerciseLibrary.objects.create(
        name=name,
        description=description or name,
        muscle_group=muscle_group,
        difficulty=difficulty,
        exercise_type=exercise_type,
    )
    from django.urls import reverse
    url = reverse('programs:exercise_library')
    params = []
    if type_val := request.POST.get('type_filter', ''):
        params.append(f'type={type_val}')
    elif muscle_group:
        params.append(f'muscle={muscle_group}')
    if request.POST.get('generate_image') == '1':
        params.append(f'autogen={ex.pk}')
    if params:
        url += '?' + '&'.join(params)
    return redirect(url)


@login_required
@require_POST
def add_exercise_to_day(request):
    """AJAX: add an exercise from the library to a program day."""
    data = json.loads(request.body)
    day = get_object_or_404(ProgramDay, pk=data['day_pk'])
    ex = get_object_or_404(ExerciseLibrary, pk=data['exercise_pk'])
    order = day.exercises.count()
    pe = ProgramExercise.objects.create(
        program_day=day,
        exercise=ex,
        sets=int(data.get('sets', 3)),
        reps=str(data.get('reps', '10-12')),
        order=order,
        confirmed=True,
    )
    return JsonResponse({
        'status': 'ok',
        'pk': pe.pk,
        'exercise_pk': ex.pk,
        'name': ex.name,
        'muscle_group': ex.muscle_group,
        'muscle_group_display': ex.get_muscle_group_display(),
        'sets': pe.sets,
        'reps': pe.reps,
        'photo_url': ex.photo_url or '',
        'posture_tips': ex.posture_tips or '',
    })


@login_required
@require_POST
def delete_program_exercise(request):
    """AJAX: remove an exercise from a program day."""
    data = json.loads(request.body)
    pe = get_object_or_404(ProgramExercise, pk=data['id'])
    pe.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def update_program_exercise(request):
    """AJAX: update sets/reps/weight/notes for an existing ProgramExercise."""
    data = json.loads(request.body)
    pe = get_object_or_404(ProgramExercise, pk=data['id'])
    pe.sets = int(data.get('sets', pe.sets))
    pe.reps = str(data.get('reps', pe.reps))
    if data.get('weight_kg') is not None:
        pe.weight_kg = float(data['weight_kg']) if data['weight_kg'] != '' else None
    pe.notes = data.get('notes', pe.notes)
    pe.save()
    return JsonResponse({'status': 'ok', 'sets': pe.sets, 'reps': pe.reps})


@login_required
@require_POST
def update_program(request, pk):
    """AJAX: update program name / description."""
    program = get_object_or_404(WorkoutProgram, pk=pk)
    data = json.loads(request.body)
    if 'name' in data:
        program.name = data['name'].strip() or program.name
    if 'name_en' in data:
        program.name_en = data['name_en'].strip()
    if 'description' in data:
        program.description = data['description'].strip()
    program.save(update_fields=['name', 'name_en', 'description'])
    return JsonResponse({'status': 'ok', 'name': program.name, 'name_en': program.name_en})


@login_required
@require_POST
def update_program_day(request, pk):
    """AJAX: update day name."""
    day = get_object_or_404(ProgramDay, pk=pk)
    data = json.loads(request.body)
    if 'name' in data:
        day.name = data['name'].strip() or day.name
    if 'name_en' in data:
        day.name_en = data['name_en'].strip()
    day.save(update_fields=['name', 'name_en'])
    return JsonResponse({'status': 'ok', 'name': day.name, 'name_en': day.name_en})


@login_required
@require_POST
def ai_correct_text(request):
    data = json.loads(request.body)
    text = data.get('text', '').strip()
    field = data.get('field', '')
    if not text:
        return JsonResponse({'error': 'No text provided'}, status=400)
    corrected = correct_text(text, field)
    return JsonResponse({'corrected': corrected})


# ── Program Templates ──────────────────────────────────────────────────────────

@login_required
def template_list(request):
    """Show all saved program templates. If ?assign=<student_pk>, show assign buttons."""
    templates = ProgramTemplate.objects.prefetch_related('days__exercises').all()
    assign_student = None
    assign_pk = request.GET.get('assign')
    if assign_pk:
        assign_student = get_object_or_404(Student, pk=assign_pk)
    active_students = Student.objects.filter(is_active=True).order_by('name')
    return render(request, 'programs/template_list.html', {
        'templates': templates,
        'assign_student': assign_student,
        'active_students': active_students,
    })


@login_required
@require_POST
def save_as_template(request, pk):
    """Deep-copy a WorkoutProgram into a ProgramTemplate."""
    program = get_object_or_404(WorkoutProgram, pk=pk)
    name = request.POST.get('name', '').strip() or program.name_en or program.name
    description = request.POST.get('description', '').strip()

    tmpl = ProgramTemplate.objects.create(
        name=name,
        description=description,
        training_days=program.training_days,
    )
    for day in program.days.all():
        tday = ProgramTemplateDay.objects.create(
            template=tmpl,
            day_number=day.day_number,
            name=day.name,
            name_en=day.name_en,
            warmup_data=day.warmup_data,
            cooldown_data=day.cooldown_data,
        )
        for pe in day.exercises.filter(confirmed=True):
            ProgramTemplateExercise.objects.create(
                template_day=tday,
                exercise=pe.exercise,
                sets=pe.sets,
                reps=pe.reps,
                weight_kg=pe.weight_kg,
                order=pe.order,
            )
    return redirect('programs:template_list')


@login_required
@require_POST
def assign_template(request, template_pk):
    """Create a WorkoutProgram for a student from a template."""
    tmpl = get_object_or_404(ProgramTemplate, pk=template_pk)
    student_pk = request.POST.get('student_pk')
    student = get_object_or_404(Student, pk=student_pk)

    program = WorkoutProgram.objects.create(
        student=student,
        name=tmpl.name,
        name_en=tmpl.name,
        training_days=tmpl.training_days,
        start_date=date.today(),
    )
    for tday in tmpl.days.all():
        day = ProgramDay.objects.create(
            program=program,
            day_number=tday.day_number,
            name=tday.name,
            name_en=tday.name_en,
            warmup_data=tday.warmup_data,
            cooldown_data=tday.cooldown_data,
        )
        for tex in tday.exercises.all():
            ProgramExercise.objects.create(
                program_day=day,
                exercise=tex.exercise,
                sets=tex.sets,
                reps=tex.reps,
                weight_kg=tex.weight_kg,
                order=tex.order,
                confirmed=True,
            )
    return redirect('programs:detail', pk=program.pk)


@login_required
@require_POST
def create_all_warmup_stretch(request):
    """
    Step 1: Claude generates warm-up + stretch exercises for all muscle groups.
    Creates ExerciseLibrary entries without images yet.
    Returns JSON list of created IDs so the page can queue illustration generation.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        exercises = suggest_warmup_stretch_exercises()
        created = []
        skipped = 0
        for ex in exercises:
            name = ex.get('name', '').strip()
            muscle_group = ex.get('muscle_group', 'full_body')
            exercise_type = ex.get('exercise_type', 'warmup')
            if not name:
                continue
            if ExerciseLibrary.objects.filter(name__iexact=name).exists():
                skipped += 1
                continue
            obj = ExerciseLibrary.objects.create(
                name=name,
                description=ex.get('description', name),
                muscle_group=muscle_group,
                difficulty=ex.get('difficulty', 'beginner'),
                exercise_type=exercise_type,
            )
            created.append({'id': obj.pk, 'name': obj.name, 'exercise_type': exercise_type})
        logger.info('create_all_warmup_stretch: created=%d skipped=%d', len(created), skipped)
        return JsonResponse({'status': 'ok', 'created': created, 'skipped': skipped})
    except Exception as exc:
        logger.exception('create_all_warmup_stretch failed')
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
@require_POST
def delete_template(request, template_pk):
    tmpl = get_object_or_404(ProgramTemplate, pk=template_pk)
    tmpl.delete()
    return redirect('programs:template_list')
