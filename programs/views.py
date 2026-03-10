import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import get_language

from students.models import Student
from .models import ExerciseLibrary, WorkoutProgram, ProgramDay, ProgramExercise
from .ai import suggest_program, suggest_nutrition, correct_text, generate_exercise_illustration


@login_required
def program_list(request, student_pk):
    student = get_object_or_404(Student, pk=student_pk)
    programs = student.programs.all()
    return render(request, 'programs/program_list.html', {'student': student, 'programs': programs})


@login_required
def program_detail(request, pk):
    program = get_object_or_404(WorkoutProgram, pk=pk)
    return render(request, 'programs/program_detail.html', {'program': program})


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

            for day_data in ai_result.get('days', []):
                day = ProgramDay.objects.create(
                    program=program,
                    day_number=day_data.get('day_number', 1),
                    name=day_data.get('day_name', 'День'),
                )
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
                        pe = ProgramExercise.objects.create(
                            program_day=day,
                            exercise=library_ex,
                            sets=ex_data.get('sets', 3),
                            reps=str(ex_data.get('reps', '10')),
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
    if muscle_filter:
        exercises = exercises.filter(muscle_group=muscle_filter)

    from students.models import Student
    students = Student.objects.filter(is_active=True).prefetch_related(
        'programs__days'
    )

    return render(request, 'programs/exercise_library.html', {
        'exercises': exercises,
        'muscle_filter': muscle_filter,
        'muscle_choices': ExerciseLibrary.MUSCLE_GROUP_CHOICES,
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
    data = json.loads(request.body)
    ex = get_object_or_404(ExerciseLibrary, pk=data['id'])
    result = generate_exercise_illustration(ex.name, ex.get_muscle_group_display(), ex.description)
    ex.photo_url = result['image_url']
    ex.posture_tips = result['posture_tips']
    ex.save(update_fields=['photo_url', 'posture_tips'])
    return JsonResponse({'image_url': result['image_url'], 'posture_tips': result['posture_tips']})


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
def ai_correct_text(request):
    data = json.loads(request.body)
    text = data.get('text', '').strip()
    field = data.get('field', '')
    if not text:
        return JsonResponse({'error': 'No text provided'}, status=400)
    corrected = correct_text(text, field)
    return JsonResponse({'corrected': corrected})
