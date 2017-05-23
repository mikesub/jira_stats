from datetime import datetime
from datetime import timedelta


def hours_spent(from_date, to_date):
    first_hour = 12
    last_hour = 20
    hours_a_day = 8
    date_format = '%Y-%m-%dT%H:%M:%S.%f%z'

    start_date = datetime.strptime(from_date, date_format)
    end_date = datetime.strptime(to_date, date_format)

    first_day = min((last_hour - start_date.hour) if start_date.hour < last_hour else 0, hours_a_day)
    last_day = min((end_date.hour - first_hour) if end_date.hour > first_hour else 0, hours_a_day)

    weekday_numbers = get_weekday_numbers(start_date.date(), end_date.date())
    weekday_numbers = [x for x in weekday_numbers if x not in [5, 6]]

    if start_date.date() == end_date.date():
        if weekday_numbers:
            result = round((end_date - start_date).total_seconds()/3600)
        else:
            result = 0
    else:
        weekday_numbers = weekday_numbers[1:-1]
        result = first_day + last_day + (len(weekday_numbers) * hours_a_day)
    return result


def get_weekday_numbers(start_date, end_date):
    weekday_numbers = []
    current_date = start_date
    while current_date <= end_date:
        weekday_numbers.append(current_date.weekday())
        current_date += timedelta(days=1)
    return weekday_numbers
