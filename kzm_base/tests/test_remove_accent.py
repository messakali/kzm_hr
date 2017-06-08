# -*- coding: utf-8 -*-


from openerp.tests.common import TransactionCase


class RemoveAccents(TransactionCase):

    def setUp(self):
        super(RemoveAccents, self).setUp()

    def test_remove_accent(self):
        from openerp.addons.kzm_ma_base.controllers.tools import remove_accent as ra
        self.assertEqual(ra(u'éçôlè'), 'ecole', "The result should be ecole")
        self.assertEqual(ra('éçôlè'), 'ecole', "The result should be ecole")

    def test_to_float(self):
        from openerp.addons.kzm_ma_base.controllers.tools import to_float as tf
        self.assertEqual(tf(u'-15145'), -15145, "The result is false")
        self.assertEqual(tf('+15145'), 15145, "The result is false")
        self.assertEqual(tf('151.45'), 151.45, "The result is false")
        self.assertEqual(tf('15ds,ds14d5'), 15.145, "The result is false")
        self.assertEqual(tf('15  1 4.3*-*5'), 1509.3, "The result is false")
