import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from students.models import Student
from .models import ExerciseLibrary, WorkoutProgram, ProgramDay, ProgramExercise
from .ai import suggest_program


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
        try:
            ai_result = suggest_program(student, training_days)
        except Exception as e:
            return render(request, 'programs/program_generate.html', {
                'student': student,
                'error': str(e),
            })

        # Create program
        key_findings = ai_result.get('key_findings', [])
        program = WorkoutProgram.objects.create(
            student=student,
            name=ai_result['program_name'],
            description='\n'.join(key_findings) if key_findings else ai_result.get('description', ''),
            training_days=training_days,
            nutrition_plan=ai_result.get('nutrition'),
        )

        exercise_library = {ex.name.lower(): ex for ex in ExerciseLibrary.objects.all()}
        suggestions = []

        for day_data in ai_result['days']:
            day = ProgramDay.objects.create(
                program=program,
                day_number=day_data['day_number'],
                name=day_data['day_name'],
            )
            for order, ex_data in enumerate(day_data['exercises']):
                name_key = ex_data['name'].lower()
                # fuzzy match: try exact, then partial
                library_ex = exercise_library.get(name_key)
                if not library_ex:
                    for key, val in exercise_library.items():
                        if any(word in key for word in name_key.split() if len(word) > 3):
                            library_ex = val
                            break

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
                        'muscle_group': library_ex.get_muscle_group_display(),
                        'photo_url': library_ex.photo_url,
                        'description': library_ex.description,
                        'sets': pe.sets,
                        'reps': pe.reps,
                        'reason': ex_data.get('reason', ''),
                        'day_name': day.name,
                    })

        return render(request, 'programs/program_generate.html', {
            'student': student,
            'program': program,
            'suggestions_json': json.dumps(suggestions),
        })

    return render(request, 'programs/program_generate.html', {'student': student})


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
    return render(request, 'programs/exercise_library.html', {
        'exercises': exercises,
        'muscle_filter': muscle_filter,
        'muscle_choices': ExerciseLibrary.MUSCLE_GROUP_CHOICES,
    })
