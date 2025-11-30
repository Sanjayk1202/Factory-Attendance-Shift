import json
from datetime import datetime, date, timedelta
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import pytz

from .forms import *
from .models import *
from .shift_settings import SHIFT_TIMINGS, WEEKLY_HOURS_THRESHOLD


def manager_home(request):
    manager = get_object_or_404(Manager, admin=request.user)
    total_employees = Employee.objects.filter(division=manager.division).count()
    total_leave = LeaveReportEmployee.objects.filter(employee__division=manager.division).count()
    
    # Get attendance statistics for the division
    employees = Employee.objects.filter(division=manager.division)
    total_attendance_today = Attendance.objects.filter(
        employee__in=employees, 
        date=date.today(), 
        status=True
    ).count()
    
    # Calculate attendance percentage for today
    if total_employees > 0:
        today_attendance_percentage = (total_attendance_today / total_employees) * 100
    else:
        today_attendance_percentage = 0
    
    # Get pending leave requests
    pending_leaves = LeaveReportEmployee.objects.filter(
        employee__division=manager.division,
        status=0
    ).count()
    
    # Get pending overtime requests
    pending_overtime = OvertimeApplication.objects.filter(
        employee__division=manager.division,
        status=0
    ).count()
    
    context = {
        'page_title': 'Manager Panel - ' + str(manager.admin.last_name) + ' (' + str(manager.division) + ')',
        'total_employees': total_employees,
        'total_attendance_today': total_attendance_today,
        'today_attendance_percentage': round(today_attendance_percentage, 2),
        'total_leave': total_leave,
        'pending_leaves': pending_leaves,
        'pending_overtime': pending_overtime,
    }
    return render(request, 'manager_template/home_content.html', context)


def manager_manage_employees(request):
    """Manager view to see employees in their division"""
    manager = get_object_or_404(Manager, admin=request.user)
    employees = Employee.objects.filter(division=manager.division)
    
    context = {
        'employees': employees,
        'page_title': 'Manage Team Employees'
    }
    return render(request, "manager_template/manage_employees.html", context)


def manager_view_attendance(request):
    manager = get_object_or_404(Manager, admin=request.user)
    employees = Employee.objects.filter(division=manager.division)
    
    if request.method == 'POST':
        selected_date = request.POST.get('date')
        try:
            attendance_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            attendance_records = Attendance.objects.filter(
                employee__in=employees,
                date=attendance_date
            ).select_related('employee')
            
            # Calculate duration for each record
            attendance_data = []
            for record in attendance_records:
                duration = None
                if record.check_in and record.check_out:
                    # Calculate duration in hours and minutes
                    check_in_dt = datetime.combine(record.date, record.check_in)
                    check_out_dt = datetime.combine(record.date, record.check_out)
                    time_diff = check_out_dt - check_in_dt
                    total_seconds = int(time_diff.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    duration = f"{hours}h {minutes}m"
                
                attendance_data.append({
                    'record': record,
                    'duration': duration
                })
            
            context = {
                'attendance_data': attendance_data,
                'selected_date': selected_date,
                'page_title': f'Attendance for {selected_date}'
            }
            return render(request, 'manager_template/manager_view_attendance.html', context)
        except Exception as e:
            messages.error(request, "Invalid date format")
    
    # Default: show today's attendance
    today = date.today()
    today_attendance = Attendance.objects.filter(
        employee__in=employees,
        date=today
    ).select_related('employee')
    
    # Calculate duration for each record
    attendance_data = []
    for record in today_attendance:
        duration = None
        if record.check_in and record.check_out:
            # Calculate duration in hours and minutes
            check_in_dt = datetime.combine(record.date, record.check_in)
            check_out_dt = datetime.combine(record.date, record.check_out)
            time_diff = check_out_dt - check_in_dt
            total_seconds = int(time_diff.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            duration = f"{hours}h {minutes}m"
        
        attendance_data.append({
            'record': record,
            'duration': duration
        })
    
    context = {
        'attendance_data': attendance_data,
        'selected_date': today.strftime("%Y-%m-%d"),
        'page_title': "Today's Attendance"
    }
    return render(request, 'manager_template/manager_view_attendance.html', context)


def manager_apply_leave(request):
    form = LeaveReportManagerForm(request.POST or None)
    manager = get_object_or_404(Manager, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportManager.objects.filter(manager=manager),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.manager = manager
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('manager_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "manager_template/manager_apply_leave.html", context)


def manager_feedback(request):
    form = FeedbackManagerForm(request.POST or None)
    manager = get_object_or_404(Manager, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackManager.objects.filter(manager=manager),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.manager = manager
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('manager_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "manager_template/manager_feedback.html", context)


def manager_view_profile(request):
    manager = get_object_or_404(Manager, admin=request.user)
    form = ManagerEditForm(request.POST or None, request.FILES or None,instance=manager)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = manager.admin
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
                manager.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('manager_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "manager_template/manager_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "manager_template/manager_view_profile.html", context)

    return render(request, "manager_template/manager_view_profile.html", context)


@csrf_exempt
def manager_fcmtoken(request):
    token = request.POST.get('token')
    try:
        manager_user = get_object_or_404(CustomUser, id=request.user.id)
        manager_user.fcm_token = token
        manager_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def manager_view_notification(request):
    manager = get_object_or_404(Manager, admin=request.user)
    notifications = NotificationManager.objects.filter(manager=manager)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "manager_template/manager_view_notification.html", context)


def manager_add_salary(request):
    manager = get_object_or_404(Manager, admin=request.user)
    departments = Department.objects.filter(division=manager.division)
    context = {
        'page_title': 'Salary Upload',
        'departments': departments
    }
    if request.method == 'POST':
        try:
            employee_id = request.POST.get('employee_list')
            department_id = request.POST.get('department')
            base = request.POST.get('base')
            ctc = request.POST.get('ctc')
            employee = get_object_or_404(Employee, id=employee_id)
            department = get_object_or_404(Department, id=department_id)
            try:
                data = EmployeeSalary.objects.get(
                    employee=employee, department=department)
                data.ctc = ctc
                data.base = base
                data.save()
                messages.success(request, "Scores Updated")
            except:
                salary = EmployeeSalary(employee=employee, department=department, base=base, ctc=ctc)
                salary.save()
                messages.success(request, "Scores Saved")
        except Exception as e:
            messages.warning(request, "Error Occured While Processing Form")
    return render(request, "manager_template/manager_add_salary.html", context)


@csrf_exempt
def fetch_employee_salary(request):
    try:
        department_id = request.POST.get('department')
        employee_id = request.POST.get('employee')
        employee = get_object_or_404(Employee, id=employee_id)
        department = get_object_or_404(Department, id=department_id)
        salary = EmployeeSalary.objects.get(employee=employee, department=department)
        salary_data = {
            'ctc': salary.ctc,
            'base': salary.base
        }
        return HttpResponse(json.dumps(salary_data))
    except Exception as e:
        return HttpResponse('False')


@csrf_exempt
def get_employees(request):
    """Get employees by department (AJAX)"""
    department_id = request.POST.get('department')
    try:
        department = get_object_or_404(Department, id=department_id)
        employees = Employee.objects.filter(department=department)
        
        employee_data = []
        for employee in employees:
            employee_data.append({
                'id': employee.id,
                'name': f"{employee.admin.first_name} {employee.admin.last_name}",
                'shift': employee.shift.name if employee.shift else 'No Shift'
            })
        
        return JsonResponse(json.dumps(employee_data), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def manager_notify_employees(request):
    manager = get_object_or_404(Manager, admin=request.user)
    form = ManagerEmployeeNotificationForm(request.POST or None, manager=manager)
    
    if request.method == 'POST':
        if form.is_valid():
            try:
                notification = form.save(commit=False)
                notification.manager = manager
                notification.save()
                
                # Send notifications to selected employees or department
                if notification.employee:
                    # Send to specific employee
                    send_manager_employee_notification(notification.employee, notification.message)
                elif notification.department:
                    # Send to all employees in department
                    employees = Employee.objects.filter(department=notification.department)
                    for employee in employees:
                        send_manager_employee_notification(employee, notification.message)
                
                messages.success(request, "Notification sent successfully!")
                return redirect(reverse('manager_notify_employees'))
            except Exception as e:
                messages.error(request, f"Could not send notification: {str(e)}")
    
    # Get notification history
    notification_history = ManagerEmployeeNotification.objects.filter(manager=manager).order_by('-created_at')
    
    context = {
        'form': form,
        'notification_history': notification_history,
        'page_title': 'Send Notifications to Employees'
    }
    return render(request, "manager_template/manager_notify_employees.html", context)


def send_manager_employee_notification(employee, message):
    """Helper function to send notification to employee from manager"""
    try:
        # Save to database
        NotificationEmployee.objects.create(
            employee=employee,
            message=f"From Manager: {message}"
        )
        
        # Here you would typically send push notification
        # For now, we'll just log it
        print(f"Notification sent to {employee}: {message}")
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


def view_employee_leave(request):
    """Manager views employee leave applications"""
    manager = get_object_or_404(Manager, admin=request.user)
    
    if request.method != 'POST':
        # Get all leave applications from employees in manager's division
        allLeave = LeaveReportEmployee.objects.filter(
            employee__division=manager.division
        ).order_by('-created_at')
        
        context = {
            'allLeave': allLeave,
            'page_title': 'Employee Leave Applications'
        }
        return render(request, "manager_template/employee_leave_view.html", context)
    else:
        # Handle leave approval/rejection
        id = request.POST.get('id')
        status = request.POST.get('status')
        if status == '1':
            status = 1
        else:
            status = -1
        
        try:
            leave = get_object_or_404(LeaveReportEmployee, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


def view_overtime_applications(request):
    """Manager views and processes overtime applications"""
    manager = get_object_or_404(Manager, admin=request.user)
    
    if request.method != 'POST':
        # Get all overtime applications from employees in manager's division
        overtime_apps = OvertimeApplication.objects.filter(
            employee__division=manager.division
        ).order_by('-created_at')
        
        context = {
            'overtime_apps': overtime_apps,
            'page_title': 'Overtime Applications'
        }
        return render(request, "manager_template/overtime_applications.html", context)
    else:
        # Handle overtime approval/rejection
        id = request.POST.get('id')
        status = request.POST.get('status')
        if status == '1':
            status = 1
        else:
            status = -1
        
        try:
            overtime = get_object_or_404(OvertimeApplication, id=id)
            overtime.status = status
            
            # If approved, update employee's overtime records
            if status == 1:
                employee = overtime.employee
                employee.total_overtime_hours += overtime.hours
                employee.overtime_remaining += overtime.hours
                employee.save()
            
            overtime.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


def get_employee_overtime_summary(request):
    """Get overtime summary for an employee (AJAX)"""
    employee_id = request.GET.get('employee_id')
    try:
        employee = get_object_or_404(Employee, id=employee_id)
        data = {
            'total_overtime_hours': employee.total_overtime_hours,
            'overtime_remaining': employee.overtime_remaining,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)