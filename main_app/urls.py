"""office_ops URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from main_app.EditSalaryView import EditSalaryView

from . import ceo_views, manager_views, employee_views, views, shift_views

urlpatterns = [
    path("", views.login_page, name='login_page'),
    path("get_attendance", views.get_attendance, name='get_attendance'),
    path("firebase-messaging-sw.js", views.showFirebaseJS, name='showFirebaseJS'),
    path("doLogin/", views.doLogin, name='user_login'),
    path("logout_user/", views.logout_user, name='user_logout'),
    path("admin/home/", ceo_views.admin_home, name='admin_home'),
    path("manager/add", ceo_views.add_manager, name='add_manager'),
    path("division/add", ceo_views.add_division, name='add_division'),
    path("send_employee_notification/", ceo_views.send_employee_notification,
         name='send_employee_notification'),
    path("send_manager_notification/", ceo_views.send_manager_notification,
         name='send_manager_notification'),
    path("admin_notify_employee", ceo_views.admin_notify_employee,
         name='admin_notify_employee'),
    path("admin_notify_manager", ceo_views.admin_notify_manager,
         name='admin_notify_manager'),
    path("admin_view_profile", ceo_views.admin_view_profile,
         name='admin_view_profile'),
    path("check_email_availability", ceo_views.check_email_availability,
         name="check_email_availability"),
    path("employee/view/feedback/", ceo_views.employee_feedback_message,
         name="employee_feedback_message",),
    path("manager/view/feedback/", ceo_views.manager_feedback_message,
         name="manager_feedback_message",),
    path("employee/view/leave/", ceo_views.view_employee_leave_ceo, 
         name="view_employee_leave",),  # Updated to redirect
    path("manager/view/leave/", ceo_views.view_manager_leave, name="view_manager_leave",),
    path("attendance/view/", ceo_views.admin_view_attendance,
         name="admin_view_attendance",),
    path("attendance/fetch/", ceo_views.get_admin_attendance,
         name='get_admin_attendance'),
    path("employee/add/", ceo_views.add_employee, name='add_employee'),
    path("department/add/", ceo_views.add_department, name='add_department'),
    path("manager/manage/", ceo_views.manage_manager, name='manage_manager'),
    path("employee/manage/", ceo_views.manage_employee, name='manage_employee'),
    path("division/manage/", ceo_views.manage_division, name='manage_division'),
    path("department/manage/", ceo_views.manage_department, name='manage_department'),
    path("manager/edit/<int:manager_id>", ceo_views.edit_manager, name='edit_manager'),
    path("manager/delete/<int:manager_id>",
         ceo_views.delete_manager, name='delete_manager'),

    path("division/delete/<int:division_id>",
         ceo_views.delete_division, name='delete_division'),

    path("department/delete/<int:department_id>",
         ceo_views.delete_department, name='delete_department'),

    path("employee/delete/<int:employee_id>",
         ceo_views.delete_employee, name='delete_employee'),
    path("employee/edit/<int:employee_id>",
         ceo_views.edit_employee, name='edit_employee'),
    path("division/edit/<int:division_id>",
         ceo_views.edit_division, name='edit_division'),
    path("department/edit/<int:department_id>",
         ceo_views.edit_department, name='edit_department'),
     
     # Shift Scheduling URLs
    path("manager/generate_schedule/", shift_views.generate_shift_schedule, 
         name='generate_shift_schedule'),
    path("shift_calendar/", shift_views.view_shift_calendar, 
         name='view_shift_calendar'),
    path("shift_events/", shift_views.get_shift_events, 
         name='get_shift_events'),
    path("update_shift/", shift_views.update_shift_assignment, 
         name='update_shift_assignment'),
    path("notify_absent/", shift_views.notify_absent_employees, 
         name='notify_absent_employees'),

   # Manager
path("manager/home/", manager_views.manager_home, name='manager_home'),
path("manager/apply/leave/", manager_views.manager_apply_leave,
     name='manager_apply_leave'),
path("manager/feedback/", manager_views.manager_feedback, name='manager_feedback'),
path("manager/view/profile/", manager_views.manager_view_profile,
     name='manager_view_profile'),
path("manager/view/attendance/", manager_views.manager_view_attendance,
     name='manager_view_attendance'),
path("manager/fcmtoken/", manager_views.manager_fcmtoken, name='manager_fcmtoken'),
path("manager/view/notification/", manager_views.manager_view_notification,
     name="manager_view_notification"),
path("manager/salary/add/", manager_views.manager_add_salary, name='manager_add_salary'),
path("manager/salary/edit/", EditSalaryView.as_view(),
     name='edit_employee_salary'),
path('manager/salary/fetch/', manager_views.fetch_employee_salary,
     name='fetch_employee_salary'),
path('manager/employees/fetch/', manager_views.get_employees, name='get_employees'),  # ADD THIS LINE
    # New Manager URLs
    path("manager/notify/employees/", manager_views.manager_notify_employees,
         name='manager_notify_employees'),
    path("manager/view/employee/leave/", manager_views.view_employee_leave,
         name='manager_view_employee_leave'),
    path("manager/view/overtime/", manager_views.view_overtime_applications,
         name='manager_view_overtime'),
    path("manager/overtime/summary/", manager_views.get_employee_overtime_summary,
         name='get_employee_overtime_summary'),
    path("manager/manage_employees/", manager_views.manager_manage_employees, name='manager_manage_employees'),



    # Employee
    path("employee/home/", employee_views.employee_home, name='employee_home'),
    path("employee/check-in/", employee_views.employee_check_in, name='employee_check_in'),
    path("employee/check-out/", employee_views.employee_check_out, name='employee_check_out'),
    path("employee/view/attendance/", employee_views.employee_view_attendance,
         name='employee_view_attendance'),
    path("employee/apply/leave/", employee_views.employee_apply_leave,
         name='employee_apply_leave'),
    path("employee/shift_schedule/", shift_views.employee_shift_schedule, name='employee_shift_schedule'),
    path("employee/apply/overtime/", employee_views.employee_apply_overtime,
         name='employee_apply_overtime'),
    path("employee/feedback/", employee_views.employee_feedback,
         name='employee_feedback'),
    path("employee/view/profile/", employee_views.employee_view_profile,
         name='employee_view_profile'),
    path("employee/fcmtoken/", employee_views.employee_fcmtoken,
         name='employee_fcmtoken'),
    path("employee/view/notification/", employee_views.employee_view_notification,
         name="employee_view_notification"),
    path('employee/view/salary/', employee_views.employee_view_salary,
         name='employee_view_salary'),

]