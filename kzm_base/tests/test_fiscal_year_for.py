# -*- coding: utf-8 -*-


from openerp.tests.common import TransactionCase

class FiscalYearFor(TransactionCase):

    def setUp(self):
        super(FiscalYearFor, self).setUp()

    def test_with_datetime(self):
        from openerp.addons.kzm_ma_base.controllers.tools import fiscal_year_for as fyf
        from datetime import datetime
        dt_from, dt_to = fyf("2010-06-09","2016-02-26", 0)
        self.assertEqual(dt_from, '2015-06-09', "The result should be 2015-06-09")
        self.assertEqual(dt_to, '2016-06-08', "The result should be 2016-06-08")
        dt_from, dt_to = fyf("2010-06-09","2016-02-26", -1)
        self.assertEqual(dt_from, '2014-06-09', "The result should be 2014-06-09")
        self.assertEqual(dt_to, '2015-06-08', "The result should be 2015-06-08")
        dt_from, dt_to = fyf("2010-01-01","2016-01-01", 0)
        self.assertEqual(dt_from, '2016-01-01', "The result should be 2016-01-01")
        self.assertEqual(dt_to, '2016-12-31', "The result should be 2016-12-31")
