import json
import math
from datetime import datetime, date, timedelta
from django.utils import timezone
import pytz

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *
from .shift_settings import SHIFT_TIMINGS, WEEKLY_HOURS_THRESHOLD


def employee_home(request):
    employee = get_object_or_404(Employee, admin=request.user)
    
    # Get Japan timezone
    japan_tz = pytz.timezone('Asia/Tokyo')
    
    # Get today's date in Japan timezone
    now_japan = timezone.now().astimezone(japan_tz)
    today = now_japan.date()
    
    # Get today's attendance
    today_attendance = Attendance.objects.filter(employee=employee, date=today).first()
    
    # Convert UTC times to Japan time for display
    if today_attendance and today_attendance.check_in:
        # Convert check_in time from UTC to Japan time
        check_in_utc = datetime.combine(today, today_attendance.check_in)
        check_in_utc = timezone.make_aware(check_in_utc, timezone.utc)
        today_attendance.check_in_japan = check_in_utc.astimezone(japan_tz).time()
    
    if today_attendance and today_attendance.check_out:
        # Convert check_out time from UTC to Japan time
        check_out_utc = datetime.combine(today, today_attendance.check_out)
        check_out_utc = timezone.make_aware(check_out_utc, timezone.utc)
        today_attendance.check_out_japan = check_out_utc.astimezone(japan_tz).time()
    
    # Calculate attendance statistics
    total_attendance = Attendance.objects.filter(employee=employee).count()
    total_present = Attendance.objects.filter(employee=employee, status=True).count()
    
    if total_attendance == 0:
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present/total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    
    # Get recent attendance (last 7 days) with calculated duration
    start_date = today - timedelta(days=7)
    recent_attendance_data = []
    recent_attendance = Attendance.objects.filter(
        employee=employee, 
        date__gte=start_date
    ).order_by('-date')
    
    for attendance in recent_attendance:
        # Convert UTC times to Japan time for display
        check_in_japan = None
        check_out_japan = None
        duration = None
        
        if attendance.check_in:
            check_in_utc = datetime.combine(attendance.date, attendance.check_in)
            check_in_utc = timezone.make_aware(check_in_utc, timezone.utc)
            check_in_japan = check_in_utc.astimezone(japan_tz).time()
        
        if attendance.check_out:
            check_out_utc = datetime.combine(attendance.date, attendance.check_out)
            check_out_utc = timezone.make_aware(check_out_utc, timezone.utc)
            check_out_japan = check_out_utc.astimezone(japan_tz).time()
            
            # Calculate duration in hours and minutes
            if check_in_japan:
                check_in_dt = datetime.combine(attendance.date, check_in_japan)
                check_out_dt = datetime.combine(attendance.date, check_out_japan)
                time_diff = check_out_dt - check_in_dt
                total_seconds = int(time_diff.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                duration = f"{hours}h {minutes}m"
        
        recent_attendance_data.append({
            'attendance': attendance,
            'check_in_japan': check_in_japan,
            'check_out_japan': check_out_japan,
            'duration': duration
        })
    
    # Get overtime summary
    overtime_summary = {
        'total_hours': employee.total_overtime_hours,
        'remaining_hours': employee.overtime_remaining,
    }
    
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'today_attendance': today_attendance,
        'recent_attendance_data': recent_attendance_data,
        'current_time': now_japan,
        'overtime_summary': overtime_summary,
        'page_title': 'Employee Homepage'
    }
    return render(request, 'employee_template/home_content.html', context)


@csrf_exempt
def employee_check_in(request):
    if request.method == 'POST':
        employee = get_object_or_404(Employee, admin=request.user)
        
        # Get current time in UTC (since TIME_ZONE = 'UTC')
        now_utc = timezone.now()
        today = now_utc.date()
        current_time = now_utc.time()
        
        # Check if already checked in today
        existing_attendance = Attendance.objects.filter(employee=employee, date=today).first()
        
        if existing_attendance:
            if existing_attendance.check_in:
                return JsonResponse({'success': False, 'message': 'You have already checked in today!'})
        
        # Check for late arrival
        is_late = False
        if employee.shift:
            shift_config = SHIFT_TIMINGS.get(employee.shift.name)
            if shift_config:
                shift_start = datetime.strptime(shift_config['start_time'], '%H:%M:%S').time()
                late_threshold = timedelta(minutes=shift_config['late_threshold_minutes'])
                
                current_dt = datetime.combine(today, current_time)
                shift_start_dt = datetime.combine(today, shift_start)
                
                if current_dt > shift_start_dt + late_threshold:
                    is_late = True
                    # Notify manager about late arrival
                    notify_manager_about_timing(employee, f"checked in late at {current_time}")
        
        # Create or update attendance record (store in UTC)
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'check_in': current_time, 
                'status': True,
                'is_late': is_late
            }
        )
        
        if not created:
            attendance.check_in = current_time
            attendance.status = True
            attendance.is_late = is_late
            attendance.save()
        
        # Convert to Japan time for response message
        japan_tz = pytz.timezone('Asia/Tokyo')
        current_time_japan = now_utc.astimezone(japan_tz)
        
        message = 'Check-in successful!'
        if is_late:
            message += ' (Late arrival noted)'
        
        return JsonResponse({
            'success': True, 
            'message': message, 
            'check_in_time': current_time_japan.strftime('%H:%M'),
            'is_late': is_late
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@csrf_exempt
def employee_check_out(request):
    if request.method == 'POST':
        employee = get_object_or_404(Employee, admin=request.user)
        
        # Get current time in UTC (since TIME_ZONE = 'UTC')
        now_utc = timezone.now()
        today = now_utc.date()
        current_time = now_utc.time()
        
        # Check if checked in today
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        
        if not attendance or not attendance.check_in:
            return JsonResponse({'success': False, 'message': 'You need to check in first!'})
        
        if attendance.check_out:
            return JsonResponse({'success': False, 'message': 'You have already checked out today!'})
        
        # Check for early departure
        is_early_departure = False
        if employee.shift:
            shift_config = SHIFT_TIMINGS.get(employee.shift.name)
            if shift_config:
                shift_end = datetime.strptime(shift_config['end_time'], '%H:%M:%S').time()
                early_threshold = timedelta(minutes=shift_config['early_departure_minutes'])
                
                current_dt = datetime.combine(today, current_time)
                shift_end_dt = datetime.combine(today, shift_end)
                
                if current_dt < shift_end_dt - early_threshold:
                    is_early_departure = True
                    # Notify manager about early departure
                    notify_manager_about_timing(employee, f"checked out early at {current_time}")
        
        # Check weekly hours for overtime notification
        weekly_hours = calculate_weekly_hours(employee)
        if weekly_hours > WEEKLY_HOURS_THRESHOLD:
            notify_manager_about_overtime(employee, weekly_hours)
        
        # Update check-out time (store in UTC)
        attendance.check_out = current_time
        attendance.is_early_departure = is_early_departure
        attendance.save()
        
        # Convert to Japan time for response message
        japan_tz = pytz.timezone('Asia/Tokyo')
        current_time_japan = now_utc.astimezone(japan_tz)
        
        message = 'Check-out successful!'
        if is_early_departure:
            message += ' (Early departure noted)'
        
        return JsonResponse({
            'success': True, 
            'message': message, 
            'check_out_time': current_time_japan.strftime('%H:%M'),
            'is_early_departure': is_early_departure
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def notify_manager_about_timing(employee, action):
    """Notify manager about employee's late/early timing"""
    try:
        # Get the manager for the employee's division
        managers = Manager.objects.filter(division=employee.division)
        for manager in managers:
            message = f"Employee {employee} {action}"
            NotificationManager.objects.create(
                manager=manager,
                message=message
            )
    except Exception as e:
        print(f"Error notifying manager: {e}")


def notify_manager_about_overtime(employee, weekly_hours):
    """Notify manager about employee exceeding weekly hours"""
    try:
        managers = Manager.objects.filter(division=employee.division)
        for manager in managers:
            message = f"Employee {employee} has worked {weekly_hours:.1f} hours this week (exceeds {WEEKLY_HOURS_THRESHOLD} hours)"
            NotificationManager.objects.create(
                manager=manager,
                message=message
            )
    except Exception as e:
        print(f"Error notifying manager about overtime: {e}")


def calculate_weekly_hours(employee):
    """Calculate total working hours for the current week"""
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    
    weekly_attendance = Attendance.objects.filter(
        employee=employee,
        date__range=[start_of_week, end_of_week],
        check_in__isnull=False,
        check_out__isnull=False
    )
    
    total_hours = 0
    for attendance in weekly_attendance:
        check_in_dt = datetime.combine(attendance.date, attendance.check_in)
        check_out_dt = datetime.combine(attendance.date, attendance.check_out)
        duration = check_out_dt - check_in_dt
        total_hours += duration.total_seconds() / 3600  # Convert to hours
    
    return total_hours


def employee_view_attendance(request):
    employee = get_object_or_404(Employee, admin=request.user)
    
    if request.method == 'POST':
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
            
            attendance_records = Attendance.objects.filter(
                employee=employee,
                date__range=(start_date, end_date)
            ).order_by('-date')
            
            # Convert times to Japan timezone
            japan_tz = pytz.timezone('Asia/Tokyo')
            attendance_data = []
            for record in attendance_records:
                check_in_japan = None
                check_out_japan = None
                
                if record.check_in:
                    check_in_utc = datetime.combine(record.date, record.check_in)
                    check_in_utc = timezone.make_aware(check_in_utc, timezone.utc)
                    check_in_japan = check_in_utc.astimezone(japan_tz).strftime('%H:%M')
                
                if record.check_out:
                    check_out_utc = datetime.combine(record.date, record.check_out)
                    check_out_utc = timezone.make_aware(check_out_utc, timezone.utc)
                    check_out_japan = check_out_utc.astimezone(japan_tz).strftime('%H:%M')
                
                data = {
                    "date": record.date.strftime("%Y-%m-%d"),
                    "check_in": check_in_japan if check_in_japan else "Not checked in",
                    "check_out": check_out_japan if check_out_japan else "Not checked out",
                    "status": "Present" if record.status else "Absent",
                    "is_late": record.is_late,
                    "is_early_departure": record.is_early_departure
                }
                attendance_data.append(data)
            
            return JsonResponse(json.dumps(attendance_data), safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # Default: show last 30 days attendance
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    attendance_history = Attendance.objects.filter(
        employee=employee,
        date__range=(start_date, end_date)
    ).order_by('-date')
    
    context = {
        'attendance_history': attendance_history,
        'page_title': 'View Attendance History'
    }
    return render(request, 'employee_template/employee_view_attendance.html', context)


def employee_apply_leave(request):
    form = LeaveReportEmployeeForm(request.POST or None)
    employee = get_object_or_404(Employee, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportEmployee.objects.filter(employee=employee),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.employee = employee
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('employee_apply_leave'))
            except Exception as e:
                messages.error(request, "Could not submit: " + str(e))
        else:
            messages.error(request, "Form has errors!")
    return render(request, "employee_template/employee_apply_leave.html", context)


def employee_apply_overtime(request):
    form = OvertimeApplicationForm(request.POST or None)
    employee = get_object_or_404(Employee, admin_id=request.user.id)
    
    if request.method == 'POST':
        if form.is_valid():
            try:
                overtime = form.save(commit=False)
                overtime.employee = employee
                
                # Calculate overtime hours
                start_dt = datetime.combine(overtime.date, overtime.start_time)
                end_dt = datetime.combine(overtime.date, overtime.end_time)
                duration = end_dt - start_dt
                overtime.hours = duration.total_seconds() / 3600  # Convert to hours
                
                overtime.save()
                messages.success(request, "Overtime application submitted for review")
                return redirect(reverse('employee_apply_overtime'))
            except Exception as e:
                messages.error(request, "Could not submit: " + str(e))
        else:
            messages.error(request, "Form has errors!")
    
    # Get overtime history
    overtime_history = OvertimeApplication.objects.filter(employee=employee).order_by('-created_at')
    
    context = {
        'form': form,
        'overtime_history': overtime_history,
        'page_title': 'Apply for Overtime'
    }
    return render(request, "employee_template/employee_apply_overtime.html", context)


def employee_feedback(request):
    form = FeedbackEmployeeForm(request.POST or None)
    employee = get_object_or_404(Employee, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackEmployee.objects.filter(employee=employee),
        'page_title': 'Employee Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.employee = employee
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('employee_feedback'))
            except Exception as e:
                messages.error(request, "Could not Submit: " + str(e))
        else:
            messages.error(request, "Form has errors!")
    return render(request, "employee_template/employee_feedback.html", context)


def employee_view_profile(request):
    employee = get_object_or_404(Employee, admin=request.user)
    form = EmployeeEditForm(request.POST or None, request.FILES or None,
                           instance=employee)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = employee.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                employee.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('employee_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "employee_template/employee_view_profile.html", context)


@csrf_exempt
def employee_fcmtoken(request):
    token = request.POST.get('token')
    employee_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        employee_user.fcm_token = token
        employee_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def employee_view_notification(request):
    employee = get_object_or_404(Employee, admin=request.user)
    notifications = NotificationEmployee.objects.filter(employee=employee)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "employee_template/employee_view_notification.html", context)


def employee_view_salary(request):
    employee = get_object_or_404(Employee, admin=request.user)
    salaries = EmployeeSalary.objects.filter(employee=employee)
    context = {
        'salaries': salaries,
        'page_title': "View Salary"
    }
    return render(request, "employee_template/employee_view_salary.html", context)