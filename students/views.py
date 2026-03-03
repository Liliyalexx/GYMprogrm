from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Student
from .forms import StudentForm


@login_required
def student_list(request):
    students = Student.objects.filter(is_active=True, intake_status='active')
    pending = Student.objects.filter(intake_status='pending')
    return render(request, 'students/student_list.html', {'students': students, 'pending': pending})


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return render(request, 'students/student_detail.html', {'student': student})


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
    return render(request, 'students/student_form.html', {'form': form, 'title': 'Edit Student', 'student': student})


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
