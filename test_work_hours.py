# pylint: disable=invalid-name

from work_hours import hours_spent

'''
 1  2  3  4  5  6  7
 8  9 10 11 12 13 14
15 16 17 18 19 20 21
'''


def test_rounding_hours():
    assert hours_spent('2017-05-04T19:15:00.000+0300', '2017-05-05T12:32:00.000+0300') == 1
    assert hours_spent('2017-05-04T19:15:00.000+0300', '2017-05-05T13:32:00.000+0300') == 2


def test_few_hours():
    assert hours_spent('2017-05-17T16:57:39.748+0300', '2017-05-17T18:12:57.908+0300') == 1


def test_same_hour():
    assert hours_spent('2017-05-12T13:56:22.137+0300', '2017-05-12T13:59:19.432+0300') == 0


def test_same_hour_at_night():
    assert hours_spent('2017-05-12T03:56:22.137+0300', '2017-05-12T03:59:19.432+0300') == 0


def test_same_hour_at_weekend():
    assert hours_spent('2017-05-07T13:56:22.137+0300', '2017-05-07T13:59:19.432+0300') == 0


def test_with_weekends_sharp():
    assert hours_spent('2017-05-05T12:00:00.000+0300', '2017-05-09T20:00:00.000+0300') == 24


def test_full_work_week():
    assert hours_spent('2017-05-08T12:00:00.000+0300', '2017-05-12T20:00:00.000+0300') == 40


def test_full_work_week_with_short_friday():
    assert hours_spent('2017-05-08T12:00:00.000+0300', '2017-05-12T18:00:00.000+0300') == 38


def test_full_week():
    assert hours_spent('2017-05-08T12:00:00.000+0300', '2017-05-14T20:00:00.000+0300') == 40


def test_mon_to_mon_ends_earlier():
    assert hours_spent('2017-05-08T12:00:00.000+0300', '2017-05-15T10:00:00.000+0300') == 40


def test_mon_to_mon():
    assert hours_spent('2017-05-08T12:00:00.000+0300', '2017-05-15T20:00:00.000+0300') == 48


def test_with_weekends():
    assert hours_spent('2017-05-05T14:00:00.000+0300', '2017-05-09T10:00:00.000+0300') == 14


def test_two_days_sharp():
    assert hours_spent('2017-05-04T12:00:00.000+0300', '2017-05-05T20:00:00.000+0300') == 16


def test_ends_earlier():
    assert hours_spent('2017-05-04T14:00:00.000+0300', '2017-05-09T10:00:00.000+0300') == 22


def test_starts_earlier_ends_later():
    assert hours_spent('2017-05-04T11:00:00.000+0300', '2017-05-05T21:00:00.000+0300') == 16


def test_at_night():
    assert hours_spent('2017-05-05T20:00:00.000+0300', '2017-05-08T10:00:00.000+0300') == 0


def test_at_night_ends_earlier():
    assert hours_spent('2017-05-05T20:00:00.000+0300', '2017-05-08T09:00:00.000+0300') == 0


def test_at_night_starts_ends_earlier():
    assert hours_spent('2017-05-05T21:00:00.000+0300', '2017-05-08T09:00:00.000+0300') == 0


def test_starts_at_night():
    assert hours_spent('2017-05-05T20:00:00.000+0300', '2017-05-08T13:00:00.000+0300') == 1
