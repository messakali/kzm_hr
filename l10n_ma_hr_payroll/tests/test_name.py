# -*- coding: utf-8 -*-


from openerp.tests.common import TransactionCase

class TestNomPrenom(TransactionCase):
    """
    Test using Nom/prenom instead of Name
    """

    def setUp(self):
        super(TestNomPrenom, self).setUp()
        self.emp_obj = self.env['hr.employee']

    def test_creation_with_name(self):
        employee = self.emp_obj.create({'name' : 'Ahmed Ibn toufail'})
        self.assertEqual(employee.nom, 'Ibn toufail', 'Erreur dans le nom')
        self.assertEqual(employee.prenom, 'Ahmed', 'Erreur dans le prenom')
