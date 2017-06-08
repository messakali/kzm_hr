# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from datetime import datetime


class TestPublicHolidays(TransactionCase):

    """
    Test Holidays count
    """

    def setUp(self):
        super(TestPublicHolidays, self).setUp()
        self.holiday_obj = self.env['hr.holidays.public']
        self.holiday_obj.create({
            'name': 'Aid',
            'date_start': '1999-05-11',
            'date_end': '1999-05-17',
        })

    def test_count_days(self):
        days = self.holiday_obj.count_days("1999-05-14", "1999-05-20")
        self.assertEqual(days, 4, 'Error, I get %s instead of 6' % days)
        days = self.holiday_obj.count_days(
            datetime(year=1999, month=5, day=14), "1999-05-20")
        self.assertEqual(days, 4, 'Error, I get %s instead of 6' % days)

    def test_is_free(self):
        free = self.holiday_obj.is_free("1999-05-20")
        self.assertFalse(free, '1999-05-20 is not free')
        free = self.holiday_obj.is_free("1999-05-17")
        self.assertTrue(free, '1999-05-17 is free')
        free = self.holiday_obj.is_free("1999-05-11")
        self.assertTrue(free, '1999-05-11 is free')
        free = self.holiday_obj.is_free("1999-05-14")
        self.assertTrue(free, '1999-05-14 is free')
