from django import forms
from django.forms.widgets import DateInput, TextInput
from .models import *
from .shift_settings import SHIFT_TIMINGS


class FormSettings(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormSettings, self).__init__(*args, **kwargs)
        # Here make some changes such as:
        for field in self.visible_fields():
            field.field.widget.attrs['class'] = 'form-control'


class CustomUserForm(FormSettings):
    email = forms.EmailField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')])
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea)
    password = forms.CharField(widget=forms.PasswordInput)
    widget = {
        'password': forms.PasswordInput(),
    }
    profile_pic = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)

        if kwargs.get('instance'):
            instance = kwargs.get('instance').admin.__dict__
            self.fields['password'].required = False
            for field in CustomUserForm.Meta.fields:
                self.fields[field].initial = instance.get(field)
            if self.instance.pk is not None:
                self.fields['password'].widget.attrs['placeholder'] = "Fill this only if you wish to update password"

    def clean_email(self, *args, **kwargs):
        formEmail = self.cleaned_data['email'].lower()
        if self.instance.pk is None:  # Insert
            if CustomUser.objects.filter(email=formEmail).exists():
                raise forms.ValidationError(
                    "The given email is already registered")
        else:  # Update
            dbEmail = self.Meta.model.objects.get(
                id=self.instance.pk).admin.email.lower()
            if dbEmail != formEmail:  # There has been changes
                if CustomUser.objects.filter(email=formEmail).exists():
                    raise forms.ValidationError("The given email is already registered")

        return formEmail

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'gender',  'password','profile_pic', 'address' ]


class EmployeeForm(CustomUserForm):
    shift = forms.ModelChoiceField(queryset=Shift.objects.all(), required=True)
    shift_preference = forms.ModelChoiceField(
        queryset=Shift.objects.all(), 
        required=False,
        empty_label="No Preference"
    )
    
    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Employee
        fields = CustomUserForm.Meta.fields + \
            ['division', 'department', 'shift', 'shift_preference']


class AdminForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Admin
        fields = CustomUserForm.Meta.fields


class ManagerForm(CustomUserForm):
    shift = forms.ModelChoiceField(queryset=Shift.objects.all(), required=True)
    
    def __init__(self, *args, **kwargs):
        super(ManagerForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Manager
        fields = CustomUserForm.Meta.fields + \
            ['division', 'shift']


class DivisionForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(DivisionForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['name']
        model = Division


class DepartmentForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(DepartmentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Department
        fields = ['name', 'division']


class LeaveReportManagerForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportManagerForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportManager
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackManagerForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackManagerForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackManager
        fields = ['feedback']


class LeaveReportEmployeeForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportEmployeeForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportEmployee
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackEmployeeForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackEmployeeForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackEmployee
        fields = ['feedback']


class EmployeeEditForm(CustomUserForm):
    shift = forms.ModelChoiceField(queryset=Shift.objects.all(), required=True)
    shift_preference = forms.ModelChoiceField(
        queryset=Shift.objects.all(), 
        required=False,
        empty_label="No Preference"
    )
    
    def __init__(self, *args, **kwargs):
        super(EmployeeEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Employee
        fields = CustomUserForm.Meta.fields + ['shift', 'shift_preference']


class ManagerEditForm(CustomUserForm):
    shift = forms.ModelChoiceField(queryset=Shift.objects.all(), required=True)
    
    def __init__(self, *args, **kwargs):
        super(ManagerEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Manager
        fields = CustomUserForm.Meta.fields + ['shift']


class EditSalaryForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(EditSalaryForm, self).__init__(*args, **kwargs)

    class Meta:
        model = EmployeeSalary
        fields = ['department', 'employee', 'base', 'ctc']


class OvertimeApplicationForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(OvertimeApplicationForm, self).__init__(*args, **kwargs)

    class Meta:
        model = OvertimeApplication
        fields = ['date', 'start_time', 'end_time', 'reason']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class ManagerEmployeeNotificationForm(FormSettings):
    def __init__(self, *args, **kwargs):
        manager = kwargs.pop('manager', None)
        super(ManagerEmployeeNotificationForm, self).__init__(*args, **kwargs)
        if manager:
            # Only show employees from manager's division
            self.fields['employee'].queryset = Employee.objects.filter(
                division=manager.division)
            self.fields['department'].queryset = Department.objects.filter(
                division=manager.division)

    class Meta:
        model = ManagerEmployeeNotification
        fields = ['employee', 'department', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }


# New Forms for Shift Scheduling
class DepartmentShiftRequirementForm(forms.Form):
    def __init__(self, *args, **kwargs):
        departments = kwargs.pop('departments', None)
        shifts = kwargs.pop('shifts', None)
        super(DepartmentShiftRequirementForm, self).__init__(*args, **kwargs)
        
        if departments and shifts:
            for department in departments:
                for shift in shifts:
                    if shift.name != 'N':  # Exclude No Preference from requirements
                        field_name = f"dept_{department.id}_shift_{shift.name}"
                        self.fields[field_name] = forms.IntegerField(
                            min_value=0,
                            required=False,
                            initial=0,
                            label=f"{department.name} - {shift.get_name_display()}",
                            widget=forms.NumberInput(attrs={'class': 'form-control'})
                        )


class GenerateScheduleForm(forms.Form):
    week_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Select Monday of the week to generate schedule for"
    )


class ShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = EmployeeShift
        fields = ['employee', 'shift', 'date', 'start_time', 'end_time']
        widgets = {
            'date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }