import json
import re
import threading
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from django.core.files.base import ContentFile
from programs.models import ExerciseLibrary
from .ai import (
    chat_with_coach, generate_program, analyse_posture,
    analyse_blood_test, generate_exercise_images,
    extract_signal_json, strip_signals,
)
from .models import (
    IndependentMember, MemberProgram, MemberProgramDay, MemberExercise,
    CoachConversation, CoachMessage, NutritionLog, PostureAnalysis,
    ExerciseDemo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def member_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        if not hasattr(request.user, 'member'):
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _get_active_program_summary(member):
    prog = member.programs.filter(is_active=True).first()
    if not prog:
        return ''
    days = prog.days.prefetch_related('exercises__exercise').all()
    lines = [f'Program: {prog.name}']
    for day in days:
        exs = ', '.join(e.exercise.name for e in day.exercises.all())
        lines.append(f'  Day {day.day_number} ({day.name}): {exs}')
    return '\n'.join(lines)


def _build_program_from_ai(member, extra_notes=''):
    """Call AI generator, persist to DB, return MemberProgram. Raises on failure."""
    exercise_library = list(
        ExerciseLibrary.objects.values('name', 'exercise_type', 'muscle_group', 'difficulty')
    )
    # Pull latest posture analysis to inform exercise selection
    latest_posture = member.posture_analyses.order_by('-created_at').first()
    posture_text = latest_posture.ai_analysis if latest_posture else ''
    data = generate_program(member, exercise_library, extra_notes=extra_notes, posture_analysis=posture_text)

    member.programs.filter(is_active=True).update(is_active=False)
    prog = MemberProgram.objects.create(
        member=member,
        name=data.get('name', 'My Program'),
        ai_reasoning=data.get('reasoning', ''),
        is_active=True,
    )
    for day_data in data.get('days', []):
        day = MemberProgramDay.objects.create(
            program=prog,
            day_number=day_data.get('day_number', 1),
            name=day_data.get('name', ''),
        )
        for order, ex_data in enumerate(day_data.get('exercises', [])):
            exercise = ExerciseLibrary.objects.filter(
                name__iexact=ex_data.get('exercise_name', '')
            ).first()
            if exercise:
                MemberExercise.objects.create(
                    day=day,
                    exercise=exercise,
                    sets=ex_data.get('sets', ''),
                    reps=ex_data.get('reps', ''),
                    notes=ex_data.get('notes', ''),
                    order=order,
                )
    return prog


def _generate_demo_images_for_program(prog):
    """No-op: exercise demos now use gymvisual.com GIFs from ExerciseLibrary.photo_url."""
    pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def member_register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        name = request.POST.get('name', '').strip()

        if not all([username, email, password1, name]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'members/register.html')
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'members/register.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'members/register.html')

        user = User.objects.create_user(username=username, email=email, password=password1)
        IndependentMember.objects.create(user=user, name=name, email=email)
        login(request, user)
        return redirect('members:onboarding')

    return render(request, 'members/register.html')


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

@member_required
def onboarding(request):
    member = request.user.member
    if member.onboarding_complete:
        return redirect('members:dashboard')

    if request.method == 'POST':
        step = request.POST.get('step', '1')

        if step == '1':
            member.goals = request.POST.get('goals', '').strip()
            member.health_conditions = request.POST.get('health_conditions', '').strip()
            member.activity_level = request.POST.get('activity_level', '')
            member.save(update_fields=['goals', 'health_conditions', 'activity_level'])
            return render(request, 'members/onboarding.html', {'step': 2, 'member': member})

        elif step == '2':
            dob = request.POST.get('date_of_birth', '')
            if dob:
                from datetime import datetime
                member.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
            member.gender = request.POST.get('gender', '')
            try:
                member.height_cm = float(request.POST.get('height_cm') or 0) or None
                member.weight_kg = float(request.POST.get('weight_kg') or 0) or None
            except ValueError:
                pass
            member.save(update_fields=['date_of_birth', 'gender', 'height_cm', 'weight_kg'])
            return render(request, 'members/onboarding.html', {'step': 3, 'member': member})

        elif step == '3':
            if 'doctor_prescription_file' in request.FILES:
                member.doctor_prescription_file = request.FILES['doctor_prescription_file']
            if 'blood_test_file' in request.FILES:
                member.blood_test_file = request.FILES['blood_test_file']
            member.save()

            # Auto-analyse blood test in background
            if member.blood_test_file:
                def _analyse():
                    try:
                        result = analyse_blood_test(member)
                        member.blood_analysis = result
                        member.save(update_fields=['blood_analysis'])
                    except Exception:
                        pass
                threading.Thread(target=_analyse, daemon=True).start()

            member.onboarding_complete = True
            member.save(update_fields=['onboarding_complete'])
            return redirect('members:dashboard')

    return render(request, 'members/onboarding.html', {'step': 1, 'member': member})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@member_required
def dashboard(request):
    member = request.user.member
    if not member.onboarding_complete:
        return redirect('members:onboarding')

    active_program = member.programs.filter(is_active=True).first()
    today_exercises = []
    if active_program:
        today_num = (date.today().weekday() % active_program.days.count()) + 1 if active_program.days.count() else 1
        today_day = active_program.days.filter(day_number=today_num).first()
        if today_day:
            today_exercises = list(today_day.exercises.select_related('exercise').all())

    today = date.today()
    today_nutrition = list(NutritionLog.objects.filter(member=member, logged_date=today).order_by('created_at'))
    total_cal = sum(n.total_calories for n in today_nutrition)
    today_protein = sum(n.total_protein_g for n in today_nutrition)
    today_carbs = sum(n.total_carbs_g for n in today_nutrition)
    today_fat = sum(n.total_fat_g for n in today_nutrition)

    recent_chats = member.conversations.order_by('-updated_at')[:3]

    return render(request, 'members/dashboard.html', {
        'member': member,
        'active_program': active_program,
        'today_exercises': today_exercises,
        'today_nutrition': today_nutrition,
        'total_cal': total_cal,
        'today_protein': today_protein,
        'today_carbs': today_carbs,
        'today_fat': today_fat,
        'recent_chats': recent_chats,
    })


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@member_required
def profile(request):
    member = request.user.member
    if request.method == 'POST':
        member.name = request.POST.get('name', member.name).strip()
        member.phone = request.POST.get('phone', '').strip()
        member.goals = request.POST.get('goals', '').strip()
        member.health_conditions = request.POST.get('health_conditions', '').strip()
        member.activity_level = request.POST.get('activity_level', member.activity_level)
        try:
            member.height_cm = float(request.POST.get('height_cm') or 0) or None
            member.weight_kg = float(request.POST.get('weight_kg') or 0) or None
        except ValueError:
            pass
        dob = request.POST.get('date_of_birth', '')
        if dob:
            from datetime import datetime
            member.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
        if 'photo' in request.FILES:
            member.photo = request.FILES['photo']
        if 'doctor_prescription_file' in request.FILES:
            member.doctor_prescription_file = request.FILES['doctor_prescription_file']
        if 'blood_test_file' in request.FILES:
            member.blood_test_file = request.FILES['blood_test_file']
            def _analyse():
                try:
                    result = analyse_blood_test(member)
                    member.blood_analysis = result
                    member.save(update_fields=['blood_analysis'])
                except Exception:
                    pass
            threading.Thread(target=_analyse, daemon=True).start()
        member.save()
        messages.success(request, 'Profile updated.')
        return redirect('members:profile')

    return render(request, 'members/profile.html', {'member': member})


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------

@member_required
def program_list(request):
    member = request.user.member
    programs = member.programs.prefetch_related('days__exercises__exercise').all()
    return render(request, 'members/program_list.html', {'member': member, 'programs': programs})


@member_required
def program_detail(request, pk):
    member = request.user.member
    program = get_object_or_404(MemberProgram, pk=pk, member=member)
    days = program.days.prefetch_related('exercises__exercise').all()
    total = sum(e.exercises.count() for d in days for e in [d])
    done = sum(e.completed for d in days for e in d.exercises.all())
    return render(request, 'members/program_detail.html', {
        'member': member,
        'program': program,
        'days': days,
        'total': total,
        'done': done,
    })


@member_required
@require_POST
def generate_program_view(request):
    member = request.user.member
    try:
        prog = _build_program_from_ai(member)
    except Exception as e:
        messages.error(request, f'Could not generate program: {e}')
        return redirect('members:program_list')

    threading.Thread(
        target=_generate_demo_images_for_program, args=(prog,), daemon=True
    ).start()

    messages.success(request, f'Program "{prog.name}" created!')
    return redirect('members:program_detail', pk=prog.pk)


@member_required
@require_POST
def complete_exercise(request, exercise_id):
    member = request.user.member
    item = get_object_or_404(MemberExercise, pk=exercise_id, day__program__member=member)
    if not item.completed:
        item.completed = True
        item.completed_at = timezone.now()
        item.save(update_fields=['completed', 'completed_at'])
    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# AI Coach Chat
# ---------------------------------------------------------------------------

@member_required
def chat_list(request):
    member = request.user.member
    convs = member.conversations.order_by('-updated_at')
    return render(request, 'members/chat_list.html', {'member': member, 'convs': convs})


@member_required
def chat_new(request):
    member = request.user.member
    conv = CoachConversation.objects.create(member=member, title='New conversation')
    return redirect('members:chat_room', pk=conv.pk)


@member_required
def chat_room(request, pk):
    member = request.user.member
    conv = get_object_or_404(CoachConversation, pk=pk, member=member)
    msgs = conv.messages.order_by('created_at')
    return render(request, 'members/chat_room.html', {
        'member': member,
        'conv': conv,
        'msgs': msgs,
    })


@member_required
@require_POST
def chat_send(request, pk):
    member = request.user.member
    conv = get_object_or_404(CoachConversation, pk=pk, member=member)

    try:
        body = json.loads(request.body)
        user_text = body.get('message', '').strip()
    except (json.JSONDecodeError, AttributeError):
        user_text = request.POST.get('message', '').strip()

    if not user_text:
        return JsonResponse({'error': 'Empty message'}, status=400)

    user_msg = CoachMessage.objects.create(conversation=conv, role='user', content=user_text)

    all_msgs = list(conv.messages.order_by('created_at'))
    history = [
        {'role': m.role, 'content': m.content}
        for m in all_msgs[:-1][-39:]
    ]
    program_summary = _get_active_program_summary(member)

    try:
        reply = chat_with_coach(history, user_text, member, program_summary)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Parse nutrition log
    log_data = extract_signal_json(reply, 'NUTRITION_LOG:')
    if log_data:
        try:
            NutritionLog.objects.create(
                member=member,
                logged_date=date.today(),
                raw_input=user_text,
                items=log_data.get('items', []),
                total_calories=log_data.get('total_calories', 0),
                total_protein_g=log_data.get('total_protein_g', 0),
                total_carbs_g=log_data.get('total_carbs_g', 0),
                total_fat_g=log_data.get('total_fat_g', 0),
            )
        except Exception:
            pass

    # Parse program creation signal — generate synchronously so it exists on first click
    signal = extract_signal_json(reply, 'CREATE_PROGRAM:')
    program_card = None
    if signal:
        extra_notes = (
            f"Weeks: {signal.get('weeks', 4)}, "
            f"Days per week: {signal.get('days_per_week', 3)}, "
            f"Focus: {signal.get('focus', '')}"
        )
        try:
            prog = _build_program_from_ai(member, extra_notes=extra_notes)
            threading.Thread(
                target=_generate_demo_images_for_program, args=(prog,), daemon=True
            ).start()
            program_card = {
                'name': prog.name,
                'focus': signal.get('focus', ''),
                'status': 'ready',
                'url': f'/members/program/{prog.pk}/',
            }
        except Exception as e:
            program_card = {
                'name': 'Could not create program',
                'focus': str(e),
                'status': 'error',
            }

    # Strip signal blocks from displayed reply
    clean_reply = strip_signals(reply, ['NUTRITION_LOG:', 'CREATE_PROGRAM:'])

    msg = CoachMessage.objects.create(conversation=conv, role='assistant', content=clean_reply)

    # Auto-title after first AI response
    if conv.title == 'New conversation' and conv.messages.count() <= 3:
        short = user_text[:50]
        conv.title = short + ('…' if len(user_text) > 50 else '')
        conv.save(update_fields=['title', 'updated_at'])
    else:
        conv.save(update_fields=['updated_at'])

    return JsonResponse({
        'reply': clean_reply,
        'nutrition': log_data,
        'program_card': program_card,
        'msg_id': msg.pk,
        'user_msg_id': user_msg.pk,
    })


@member_required
@require_POST
def chat_generate_program(request, pk):
    """Generate a program directly from within a conversation context."""
    member = request.user.member
    get_object_or_404(CoachConversation, pk=pk, member=member)

    try:
        body = json.loads(request.body)
        context = body.get('context', '')
    except (json.JSONDecodeError, AttributeError):
        context = ''

    try:
        prog = _build_program_from_ai(member, extra_notes=context[:300])
        threading.Thread(
            target=_generate_demo_images_for_program, args=(prog,), daemon=True
        ).start()
        return JsonResponse({
            'ok': True,
            'name': prog.name,
            'focus': '',
            'url': f'/members/program/{prog.pk}/',
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@member_required
@require_POST
def chat_edit(request, pk, msg_id):
    """Edit a user message: delete it + all subsequent messages, resend with new text."""
    member = request.user.member
    conv = get_object_or_404(CoachConversation, pk=pk, member=member)
    original = get_object_or_404(CoachMessage, pk=msg_id, conversation=conv, role='user')

    try:
        body = json.loads(request.body)
        new_text = body.get('message', '').strip()
    except (json.JSONDecodeError, AttributeError):
        new_text = ''

    if not new_text:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Delete original message and everything after it
    CoachMessage.objects.filter(
        conversation=conv,
        created_at__gte=original.created_at,
    ).delete()

    # Re-use the send logic
    user_msg = CoachMessage.objects.create(conversation=conv, role='user', content=new_text)

    all_msgs = list(conv.messages.order_by('created_at'))
    history = [{'role': m.role, 'content': m.content} for m in all_msgs[:-1][-39:]]
    program_summary = _get_active_program_summary(member)

    try:
        reply = chat_with_coach(history, new_text, member, program_summary)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    log_data = extract_signal_json(reply, 'NUTRITION_LOG:')
    if log_data:
        try:
            NutritionLog.objects.create(
                member=member,
                logged_date=date.today(),
                raw_input=new_text,
                items=log_data.get('items', []),
                total_calories=log_data.get('total_calories', 0),
                total_protein_g=log_data.get('total_protein_g', 0),
                total_carbs_g=log_data.get('total_carbs_g', 0),
                total_fat_g=log_data.get('total_fat_g', 0),
            )
        except Exception:
            pass

    signal = extract_signal_json(reply, 'CREATE_PROGRAM:')
    program_card = None
    if signal:
        extra_notes = (
            f"Weeks: {signal.get('weeks', 4)}, "
            f"Days per week: {signal.get('days_per_week', 3)}, "
            f"Focus: {signal.get('focus', '')}"
        )
        try:
            prog = _build_program_from_ai(member, extra_notes=extra_notes)
            threading.Thread(
                target=_generate_demo_images_for_program, args=(prog,), daemon=True
            ).start()
            program_card = {
                'name': prog.name,
                'focus': signal.get('focus', ''),
                'status': 'ready',
                'url': f'/members/program/{prog.pk}/',
            }
        except Exception as e:
            program_card = {
                'name': 'Could not create program',
                'focus': str(e),
                'status': 'error',
            }

    clean_reply = strip_signals(reply, ['NUTRITION_LOG:', 'CREATE_PROGRAM:'])
    ai_msg = CoachMessage.objects.create(conversation=conv, role='assistant', content=clean_reply)
    conv.save(update_fields=['updated_at'])

    return JsonResponse({
        'reply': clean_reply,
        'new_text': new_text,
        'nutrition': log_data,
        'program_card': program_card,
        'msg_id': ai_msg.pk,
        'user_msg_id': user_msg.pk,
    })


@member_required
@require_POST
def chat_delete_conv(request, pk):
    """Delete an entire conversation and all its messages."""
    member = request.user.member
    conv = get_object_or_404(CoachConversation, pk=pk, member=member)
    conv.delete()
    return JsonResponse({'ok': True})


@member_required
@require_POST
def chat_bulk_delete(request):
    """Delete multiple conversations at once."""
    member = request.user.member
    try:
        body = json.loads(request.body)
        pks = [int(pk) for pk in body.get('pks', [])]
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid request'}, status=400)
    if not pks:
        return JsonResponse({'error': 'No conversations selected'}, status=400)
    deleted, _ = CoachConversation.objects.filter(pk__in=pks, member=member).delete()
    return JsonResponse({'ok': True, 'deleted': deleted})


@member_required
@require_POST
def chat_delete_msg(request, pk, msg_id):
    """Delete a user message and all subsequent messages."""
    member = request.user.member
    conv = get_object_or_404(CoachConversation, pk=pk, member=member)
    target = get_object_or_404(CoachMessage, pk=msg_id, conversation=conv)

    deleted, _ = CoachMessage.objects.filter(
        conversation=conv,
        created_at__gte=target.created_at,
    ).delete()

    conv.save(update_fields=['updated_at'])
    return JsonResponse({'ok': True, 'deleted': deleted})


# ---------------------------------------------------------------------------
# Posture Analysis
# ---------------------------------------------------------------------------

@member_required
def posture_list(request):
    member = request.user.member
    analyses = member.posture_analyses.order_by('-created_at')
    return render(request, 'members/posture_list.html', {'member': member, 'analyses': analyses})


@member_required
def posture_upload(request):
    member = request.user.member
    if request.method == 'POST' and 'photo' in request.FILES:
        photo = request.FILES['photo']
        obj = PostureAnalysis.objects.create(member=member, photo=photo)

        def _analyse():
            try:
                analysis = analyse_posture(obj.photo)
                obj.ai_analysis = analysis
                obj.save(update_fields=['ai_analysis'])
            except Exception:
                pass
        threading.Thread(target=_analyse, daemon=True).start()

        return redirect('members:posture_detail', pk=obj.pk)

    return render(request, 'members/posture_upload.html', {'member': member})


@member_required
def posture_detail(request, pk):
    member = request.user.member
    obj = get_object_or_404(PostureAnalysis, pk=pk, member=member)
    return render(request, 'members/posture_detail.html', {'member': member, 'obj': obj})


# ---------------------------------------------------------------------------
# Nutrition Log
# ---------------------------------------------------------------------------

def _calc_targets(member):
    """Return daily calorie and macro targets based on member profile."""
    try:
        weight = float(member.weight_kg or 0)
        height = float(member.height_cm or 0)
        age = member.age or 0
        if not (weight and height and age):
            return None

        # Mifflin-St Jeor BMR
        if member.gender == 'M':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        activity_map = {
            'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55,
            'active': 1.725, 'very_active': 1.9,
        }
        multiplier = activity_map.get(member.activity_level or 'moderate', 1.55)
        tdee = bmr * multiplier

        # Adjust for goal
        goals = (member.goals or '').lower()
        if any(w in goals for w in ('lose', 'loss', 'slim', 'cut', 'deficit')):
            target_kcal = tdee - 500
        elif any(w in goals for w in ('gain', 'bulk', 'muscle', 'mass')):
            target_kcal = tdee + 300
        else:
            target_kcal = tdee

        target_kcal = max(1200, round(target_kcal))
        protein_g = round(weight * 1.8)  # 1.8g/kg
        fat_g = round(target_kcal * 0.27 / 9)  # 27% from fat
        carbs_g = round((target_kcal - protein_g * 4 - fat_g * 9) / 4)

        return {
            'calories': target_kcal,
            'protein': protein_g,
            'carbs': max(0, carbs_g),
            'fat': fat_g,
        }
    except Exception:
        return None


@member_required
def nutrition_log(request):
    member = request.user.member
    today = date.today()
    selected_date = request.GET.get('date', str(today))
    try:
        selected_date = date.fromisoformat(selected_date)
    except ValueError:
        selected_date = today

    logs = NutritionLog.objects.filter(member=member, logged_date=selected_date).order_by('created_at')
    totals = {
        'calories': sum(l.total_calories for l in logs),
        'protein': sum(l.total_protein_g for l in logs),
        'carbs': sum(l.total_carbs_g for l in logs),
        'fat': sum(l.total_fat_g for l in logs),
    }
    # Last 7 days for chart
    week = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_logs = NutritionLog.objects.filter(member=member, logged_date=d)
        week.append({'date': str(d), 'calories': sum(l.total_calories for l in day_logs)})

    # Previous-day suggestions: last unique logs from before selected_date
    suggestions = []
    if selected_date == today:
        prev_logs = (
            NutritionLog.objects
            .filter(member=member, logged_date__lt=today)
            .order_by('-logged_date', '-created_at')[:5]
        )
        suggestions = list(prev_logs)

    return render(request, 'members/nutrition.html', {
        'member': member,
        'logs': logs,
        'totals': totals,
        'targets': _calc_targets(member),
        'selected_date': selected_date,
        'today': today,
        'week': json.dumps(week),
        'suggestions': suggestions,
    })


@member_required
@require_POST
def nutrition_add_again(request, log_id):
    """Copy a past NutritionLog entry to today."""
    member = request.user.member
    original = get_object_or_404(NutritionLog, pk=log_id, member=member)
    today = date.today()
    NutritionLog.objects.create(
        member=member,
        logged_date=today,
        raw_input=original.raw_input,
        items=original.items,
        total_calories=original.total_calories,
        total_protein_g=original.total_protein_g,
        total_carbs_g=original.total_carbs_g,
        total_fat_g=original.total_fat_g,
    )
    return redirect('members:nutrition_log')


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

@member_required
def progress(request):
    member = request.user.member
    today = date.today()

    # Exercise completion this week
    week_start = today - timedelta(days=today.weekday())
    week_exercises = MemberExercise.objects.filter(
        day__program__member=member,
        completed=True,
        completed_at__date__gte=week_start,
    ).count()

    # Nutrition last 14 days
    nutrition_days = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        day_logs = NutritionLog.objects.filter(member=member, logged_date=d)
        nutrition_days.append({
            'date': d.strftime('%b %d'),
            'calories': round(sum(l.total_calories for l in day_logs)),
        })

    # Total exercises ever
    total_exercises = MemberExercise.objects.filter(
        day__program__member=member, completed=True
    ).count()

    return render(request, 'members/progress.html', {
        'member': member,
        'week_exercises': week_exercises,
        'total_exercises': total_exercises,
        'nutrition_days': json.dumps(nutrition_days),
        'blood_analysis': member.blood_analysis,
    })
