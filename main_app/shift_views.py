import json
from datetime import datetime, timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import *
from .forms import *
from .shift_scheduler import ShiftScheduler, AbsenceNotifier


def generate_shift_schedule(request):
    """
    Manager view to generate shift schedule
    """
    manager = get_object_or_404(Manager, admin=request.user)
    
    if request.method == 'POST':
        form = GenerateScheduleForm(request.POST)
        if form.is_valid():
            week_start_date = form.cleaned_data['week_start_date']
            
            # Ensure it's a Monday
            if week_start_date.weekday() != 0:
                messages.error(request, "Please select a Monday as the week start date!")
                return redirect(reverse('generate_shift_schedule'))
            
            # Check if schedule already exists
            if ShiftSchedule.objects.filter(
                division=manager.division, 
                week_start_date=week_start_date
            ).exists():
                messages.warning(request, "Schedule already exists for this week!")
                return redirect(reverse('generate_shift_schedule'))
            
            # Process requirements
            departments = Department.objects.filter(division=manager.division)
            shifts = Shift.objects.exclude(name='N')  # Exclude No Preference
            requirements = {}
            
            for dept in departments:
                for shift in shifts:
                    field_name = f"dept_{dept.id}_shift_{shift.name}"
                    requirements[field_name] = int(request.POST.get(field_name, 0))
            
            # Generate schedule
            try:
                scheduler = ShiftScheduler(manager.division, week_start_date)
                schedule = scheduler.generate_schedule(requirements, manager)
                
                # Notify employees
                notify_employees_about_schedule(schedule)
                
                messages.success(request, "Shift schedule generated successfully!")
                return redirect(reverse('view_shift_calendar'))
                
            except Exception as e:
                messages.error(request, f"Error generating schedule: {str(e)}")
        else:
            messages.error(request, "Invalid form data!")
    else:
        # Default to next Monday
        today = timezone.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        next_monday = today + timedelta(days=days_until_monday)
        
        form = GenerateScheduleForm(initial={'week_start_date': next_monday})
    
    departments = Department.objects.filter(division=manager.division)
    shifts = Shift.objects.exclude(name='N')  # Exclude No Preference
    
    context = {
        'form': form,
        'page_title': 'Generate Shift Schedule',
        'departments': departments,
        'shifts': shifts,
    }
    return render(request, 'manager_template/generate_schedule.html', context)


def employee_shift_schedule(request):
    """
    Employee view to see their own shift schedule (read-only)
    """
    if request.user.user_type != '3':  # Only for employees
        messages.error(request, "Access denied.")
        return redirect(reverse('employee_home'))
    
    employee = get_object_or_404(Employee, admin=request.user)
    context = {
        'page_title': 'My Shift Schedule',
        'employee': employee
    }
    
    # Get current and upcoming schedules
    today = timezone.now().date()
    schedules = ShiftSchedule.objects.filter(
        division=employee.division,
        week_end_date__gte=today
    ).order_by('week_start_date')
    
    context['schedules'] = schedules
    
    return render(request, 'employee_template/employee_shift_schedule.html', context)

def view_shift_calendar(request):
    """
    Calendar view for shift schedule
    """
    user = request.user
    context = {'page_title': 'Shift Calendar'}
    
    if user.user_type == '2':  # Manager
        manager = get_object_or_404(Manager, admin=user)
        schedules = ShiftSchedule.objects.filter(division=manager.division).order_by('-week_start_date')
        context['schedules'] = schedules
        context['division'] = manager.division
        context['departments'] = Department.objects.filter(division=manager.division)
        
    elif user.user_type == '1':  # CEO
        schedules = ShiftSchedule.objects.all().order_by('-week_start_date')
        context['schedules'] = schedules
        context['divisions'] = Division.objects.all()
        
    elif user.user_type == '3':  # Employee
        employee = get_object_or_404(Employee, admin=user)
        schedules = ShiftSchedule.objects.filter(division=employee.division).order_by('-week_start_date')
        context['schedules'] = schedules
        context['employee'] = employee
    
    return render(request, 'manager_template/shift_calendar.html', context)


@csrf_exempt
def get_shift_events(request):
    """
    AJAX endpoint to get shift events for calendar
    """
    schedule_id = request.GET.get('schedule_id')
    department_id = request.GET.get('department_id')
    employee_id = request.GET.get('employee_id')
    division_id = request.GET.get('division_id')
    
    events = []
    
    try:
        if schedule_id:
            shifts = EmployeeShift.objects.filter(schedule_id=schedule_id)
        elif division_id:
            # Get latest schedule for division
            latest_schedule = ShiftSchedule.objects.filter(
                division_id=division_id
            ).order_by('-week_start_date').first()
            if latest_schedule:
                shifts = EmployeeShift.objects.filter(schedule=latest_schedule)
            else:
                shifts = EmployeeShift.objects.none()
        else:
            shifts = EmployeeShift.objects.none()
        
        if department_id:
            shifts = shifts.filter(employee__department_id=department_id)
        
        if employee_id:
            shifts = shifts.filter(employee_id=employee_id)
        
        for shift in shifts:
            # Handle overnight shifts
            start_datetime = datetime.combine(shift.date, shift.start_time)
            end_datetime = datetime.combine(shift.date, shift.end_time)
            
            if shift.end_time < shift.start_time:  # Overnight shift
                end_datetime += timedelta(days=1)
            
            events.append({
                'id': shift.id,
                'title': f"{shift.employee.admin.get_full_name()} ({shift.shift.name})",
                'start': start_datetime.isoformat(),
                'end': end_datetime.isoformat(),
                'resource': {
                    'employee_id': shift.employee.id,
                    'employee_name': str(shift.employee),
                    'employee_number': shift.employee.employee_id,
                    'shift_id': shift.shift.name,
                    'department': shift.employee.department.name,
                    'is_manual_override': shift.is_manual_override,
                },
                'extendedProps': {
                    'department': shift.employee.department.name,
                    'employee_id': shift.employee.employee_id,
                }
            })
    
    except Exception as e:
        print(f"Error fetching shift events: {e}")
    
    return JsonResponse(events, safe=False)


@csrf_exempt
def update_shift_assignment(request):
    """
    AJAX endpoint to update shift assignment (drag & drop)
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            shift_id = data.get('shift_id')
            new_date = data.get('new_date')
            new_start_time = data.get('new_start_time')
            new_end_time = data.get('new_end_time')
            new_employee_id = data.get('new_employee_id')
            
            shift = get_object_or_404(EmployeeShift, id=shift_id)
            
            # Update shift
            if new_date:
                shift.date = datetime.strptime(new_date, '%Y-%m-%d').date()
            if new_start_time:
                shift.start_time = datetime.strptime(new_start_time, '%H:%M:%S').time()
            if new_end_time:
                shift.end_time = datetime.strptime(new_end_time, '%H:%M:%S').time()
            if new_employee_id:
                new_employee = get_object_or_404(Employee, id=new_employee_id)
                shift.employee = new_employee
            
            shift.is_manual_override = True
            shift.save()
            
            # Notify employee about schedule change
            notify_employee_about_schedule_change(shift.employee, shift)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


def notify_employees_about_schedule(schedule):
    """
    Notify all employees about new schedule
    """
    employees = Employee.objects.filter(division=schedule.division)
    
    for employee in employees:
        # Get employee's shifts for the week
        employee_shifts = EmployeeShift.objects.filter(
            schedule=schedule,
            employee=employee
        ).order_by('date')
        
        if employee_shifts.exists():
            shift_details = []
            for shift in employee_shifts:
                shift_details.append(
                    f"{shift.date}: {shift.shift.get_name_display()} ({shift.start_time} - {shift.end_time})"
                )
            
            message = f"Your shift schedule for {schedule.week_start_date} to {schedule.week_end_date}:\n" + "\n".join(shift_details)
        else:
            message = f"No shifts scheduled for you from {schedule.week_start_date} to {schedule.week_end_date}."
        
        NotificationEmployee.objects.create(
            employee=employee,
            message=message
        )


def notify_employee_about_schedule_change(employee, shift):
    """
    Notify employee about schedule change
    """
    message = f"Your shift has been updated: {shift.date} - {shift.shift.get_name_display()} ({shift.start_time} to {shift.end_time})"
    NotificationEmployee.objects.create(
        employee=employee,
        message=message
    )


def notify_absent_employees(request):
    """
    Manual trigger to notify about absent employees
    """
    if request.user.user_type == '2':  # Only managers
        date = request.GET.get('date')
        if date:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
            
        AbsenceNotifier.notify_managers_about_absence(date)
        messages.success(request, f"Absence notifications sent for {date}!")
    
    return redirect(reverse('manager_home'))