"""
Shift timing configurations
These can be easily modified without changing the core logic
"""

SHIFT_TIMINGS = {
    'A': {
        'name': 'Shift A',
        'start_time': '09:00:00',
        'end_time': '17:00:00',
        'description': 'Day Shift (9:00 AM - 5:00 PM)',
        'late_threshold_minutes': 10,
        'early_departure_minutes': 10,
        'duration_hours': 8,
    },
    'B': {
        'name': 'Shift B',
        'start_time': '17:00:00',
        'end_time': '01:00:00',  # Next day
        'description': 'Evening Shift (5:00 PM - 1:00 AM)',
        'late_threshold_minutes': 10,
        'early_departure_minutes': 10,
        'duration_hours': 8,
    },
    'C': {
        'name': 'Shift C',
        'start_time': '01:00:00',
        'end_time': '09:00:00',
        'description': 'Night Shift (1:00 AM - 9:00 AM)',
        'late_threshold_minutes': 10,
        'early_departure_minutes': 10,
        'duration_hours': 8,
    },
    'N': {
        'name': 'No Preference',
        'start_time': '00:00:00',
        'end_time': '00:00:00',
        'description': 'No Shift Preference - Can be assigned to any shift',
        'late_threshold_minutes': 0,
        'early_departure_minutes': 0,
        'duration_hours': 8,  # Still works 8 hours when assigned
    }
}

# Weekly working hours threshold for overtime notification
WEEKLY_HOURS_THRESHOLD = 40

# Overtime conversion rate (overtime hours to compensatory leave hours)
OVERTIME_CONVERSION_RATE = 1.0

# Factory scheduling constraints
SCHEDULING_CONSTRAINTS = {
    'max_weekly_hours': 40,
    'min_daily_hours': 8,
    'max_consecutive_shifts': 6,  # Allow continuous work but not same shift type continuously
    'min_rest_between_shifts': 8,  # hours
    'max_night_shifts_per_week': 3,
    'preference_priority_weight': 2,  # How much to prioritize employee preferences
}