import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import *
from .shift_settings import SHIFT_TIMINGS, SCHEDULING_CONSTRAINTS


class ShiftScheduler:
    def __init__(self, division, week_start_date):
        self.division = division
        self.week_start_date = week_start_date
        self.week_end_date = week_start_date + timedelta(days=6)
        self.departments = Department.objects.filter(division=division)
        self.employees = Employee.objects.filter(division=division)
        self.shifts = Shift.objects.exclude(name='N')  # Exclude 'No Preference' for assignment
        
    def generate_schedule(self, requirements, manager):
        """
        Generate schedule based on department requirements with intelligent assignment
        """
        # Create schedule record
        schedule, created = ShiftSchedule.objects.get_or_create(
            division=self.division,
            week_start_date=self.week_start_date,
            defaults={
                'week_end_date': self.week_end_date,
                'created_by': manager
            }
        )
        
        if not created:
            # Clear existing assignments if regenerating
            EmployeeShift.objects.filter(schedule=schedule).delete()
            DepartmentShiftRequirement.objects.filter(schedule=schedule).delete()
        
        # Save requirements
        for dept in self.departments:
            for shift in self.shifts:
                field_name = f"dept_{dept.id}_shift_{shift.name}"
                count = requirements.get(field_name, 0)
                if count > 0:
                    DepartmentShiftRequirement.objects.create(
                        schedule=schedule,
                        department=dept,
                        shift=shift,
                        employee_count=count
                    )
        
        # Generate assignments for each day of the week
        current_date = self.week_start_date
        while current_date <= self.week_end_date:
            self._generate_daily_schedule(schedule, current_date, requirements)
            current_date += timedelta(days=1)
            
        return schedule
    
    def _generate_daily_schedule(self, schedule, date, requirements):
        """
        Generate schedule for a specific day with intelligent assignment
        """
        # Get employees with approved leave for this date
        on_leave = LeaveReportEmployee.objects.filter(
            employee__division=self.division,
            date=date.strftime("%Y-%m-%d"),
            status=1
        ).values_list('employee_id', flat=True)
        
        available_employees = self.employees.exclude(id__in=on_leave)
        
        # Track assigned employees to avoid duplicates
        assigned_employees = set()
        employee_assignments = {}  # Track employee assignments for the day
        
        for dept in self.departments:
            dept_employees = available_employees.filter(department=dept)
            
            for shift in self.shifts:
                field_name = f"dept_{dept.id}_shift_{shift.name}"
                required_count = requirements.get(field_name, 0)
                
                if required_count > 0:
                    # Get shift timing
                    shift_config = SHIFT_TIMINGS.get(shift.name, {})
                    start_time = datetime.strptime(shift_config.get('start_time', '09:00:00'), '%H:%M:%S').time()
                    end_time = datetime.strptime(shift_config.get('end_time', '17:00:00'), '%H:%M:%S').time()
                    
                    # Select employees for this shift with priority to preferences
                    candidates = dept_employees.exclude(id__in=assigned_employees)
                    
                    # Prioritize employees based on shift preference
                    preferred_candidates = []
                    no_preference_candidates = []
                    other_candidates = []
                    
                    for emp in candidates:
                        if emp.shift_preference and emp.shift_preference.name == shift.name:
                            preferred_candidates.append(emp)
                        elif emp.shift_preference and emp.shift_preference.name == 'N':
                            no_preference_candidates.append(emp)
                        else:
                            other_candidates.append(emp)
                    
                    # Sort candidates by preference priority
                    selected_employees = (preferred_candidates + 
                                        no_preference_candidates + 
                                        other_candidates)
                    
                    # Apply weekly hours constraint
                    valid_employees = []
                    for emp in selected_employees:
                        weekly_hours = self._get_employee_weekly_hours(emp, schedule)
                        shift_hours = self._calculate_shift_hours(start_time, end_time)
                        
                        if weekly_hours + shift_hours <= emp.max_weekly_hours:
                            valid_employees.append(emp)
                    
                    # Take required number of employees
                    employees_to_assign = valid_employees[:required_count]
                    
                    for employee in employees_to_assign:
                        # Check for consecutive shift constraints
                        if not self._check_consecutive_shifts(employee, date, shift, schedule):
                            EmployeeShift.objects.create(
                                schedule=schedule,
                                employee=employee,
                                date=date,
                                shift=shift,
                                start_time=start_time,
                                end_time=end_time
                            )
                            assigned_employees.add(employee.id)
                            employee_assignments[employee.id] = shift.name
    
    def _get_employee_weekly_hours(self, employee, schedule):
        """
        Calculate total hours assigned to employee for the week
        """
        assigned_shifts = EmployeeShift.objects.filter(
            schedule=schedule,
            employee=employee
        )
        
        total_hours = 0
        for assignment in assigned_shifts:
            start_dt = datetime.combine(assignment.date, assignment.start_time)
            end_dt = datetime.combine(assignment.date, assignment.end_time)
            if end_dt < start_dt:  # Overnight shift
                end_dt += timedelta(days=1)
            duration = end_dt - start_dt
            total_hours += duration.total_seconds() / 3600
            
        return total_hours
    
    def _calculate_shift_hours(self, start_time, end_time):
        """
        Calculate shift duration in hours
        """
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = datetime.combine(datetime.today(), end_time)
        if end_dt < start_dt:  # Overnight shift
            end_dt += timedelta(days=1)
        duration = end_dt - start_dt
        return duration.total_seconds() / 3600
    
    def _check_consecutive_shifts(self, employee, date, shift, schedule):
        """
        Check if employee has too many consecutive shifts of same type
        """
        # Check previous 2 days
        prev_dates = [date - timedelta(days=1), date - timedelta(days=2)]
        consecutive_same_shifts = 0
        
        for prev_date in prev_dates:
            try:
                prev_shift = EmployeeShift.objects.get(
                    schedule=schedule,
                    employee=employee,
                    date=prev_date
                )
                if prev_shift.shift == shift:
                    consecutive_same_shifts += 1
            except EmployeeShift.DoesNotExist:
                continue
        
        return consecutive_same_shifts >= SCHEDULING_CONSTRAINTS['max_consecutive_shifts']


class AbsenceNotifier:
    @staticmethod
    def notify_managers_about_absence(date=None):
        """
        Notify managers about absent employees
        """
        if date is None:
            date = timezone.now().date()
            
        # Get all divisions with absent employees
        divisions = Division.objects.all()
        
        for division in divisions:
            # Get present employees
            present_employees = Attendance.objects.filter(
                date=date,
                status=True,
                employee__division=division
            ).values_list('employee_id', flat=True)
            
            # Get scheduled employees
            scheduled_employees = EmployeeShift.objects.filter(
                date=date,
                employee__division=division
            ).values_list('employee_id', flat=True)
            
            # Find absent employees (scheduled but not present)
            absent_employees = set(scheduled_employees) - set(present_employees)
            
            if absent_employees:
                managers = Manager.objects.filter(division=division)
                absent_list = Employee.objects.filter(id__in=absent_employees)
                
                message = f"Absent employees for {date}:\n"
                for emp in absent_list:
                    # Get employee's scheduled shift
                    try:
                        scheduled_shift = EmployeeShift.objects.get(
                            date=date,
                            employee=emp
                        )
                        message += f"- {emp} (ID: {emp.employee_id}) - Scheduled: {scheduled_shift.shift.get_name_display()}\n"
                    except EmployeeShift.DoesNotExist:
                        message += f"- {emp} (ID: {emp.employee_id}) - No shift scheduled\n"
                
                for manager in managers:
                    NotificationManager.objects.create(
                        manager=manager,
                        message=message
                    )
                    
                print(f"Sent absence notifications to {len(managers)} managers in {division.name}")