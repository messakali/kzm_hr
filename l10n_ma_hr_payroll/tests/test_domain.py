# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestDomain(TransactionCase):
    """
    Test using Nom/prenom instead of Name
    """

    def setUp(self):
        super(TestDomain, self).setUp()
        self.rubrique_obj = self.env['hr.rubrique.line']
        rubrique = self.env['hr.rubrique'].search([], limit=1)
        self.emp_obj = self.env['hr.employee']
        self.emp = self.emp_obj.create({'name' : 'John Doe'})
        self.code = rubrique.code
        self.rubrique_id = rubrique.id

    def test_domain(self):
        static_data = {
            'date_start' : False,
            'date_end' : False,
            'employee_id' : self.emp.id,
            'rubrique_id' : self.rubrique_id,
            'code' : self.code,
            'name' : 'PASS',
            'amount' : 1000,
        }
        #R1
        r1_data = dict(static_data, date_start=False, date_end=False, name='YES')
        r1 = self.rubrique_obj.create(r1_data)
        r1.should_be_done()
        #R2
        r2_data = dict(static_data, date_start='2016-04-04', date_end=False, name='YES')
        r2 = self.rubrique_obj.create(r2_data)
        r2.should_be_done()
        #R3
        r3_data = dict(static_data, date_start='2016-10-01', date_end=False, name='YES')
        r3 = self.rubrique_obj.create(r3_data)
        r3.should_be_done()
        #R4
        r4_data = dict(static_data, date_start='2016-10-31', date_end=False, name='YES')
        r4 = self.rubrique_obj.create(r4_data)
        r4.should_be_done()
        #R5
        r5_data = dict(static_data, date_start='2016-11-04', date_end=False, name='NO')
        r5 = self.rubrique_obj.create(r5_data)
        r5.should_be_done()
        #R6
        r6_data = dict(static_data, date_start=False, date_end="2016-04-04", name='NO')
        r6 = self.rubrique_obj.create(r6_data)
        r6.should_be_done()
        #R7
        r7_data = dict(static_data, date_start=False, date_end="2016-10-01", name='YES')
        r7 = self.rubrique_obj.create(r7_data)
        r7.should_be_done()
        #R8
        r8_data = dict(static_data, date_start=False, date_end="2016-10-31", name='YES')
        r8 = self.rubrique_obj.create(r8_data)
        r8.should_be_done()
        #R9
        r9_data = dict(static_data, date_start=False, date_end="2016-11-12", name='YES')
        r9 = self.rubrique_obj.create(r9_data)
        r9.should_be_done()
        #R10
        r10_data = dict(static_data, date_start="2016-03-03", date_end="2016-04-12", name='NO')
        r10 = self.rubrique_obj.create(r10_data)
        r10.should_be_done()
        #R11
        r11_data = dict(static_data, date_start="2016-05-03", date_end="2016-10-01", name='YES')
        r11 = self.rubrique_obj.create(r11_data)
        r11.should_be_done()
        #R12
        r12_data = dict(static_data, date_start="2016-05-03", date_end="2016-10-15", name='YES')
        r12 = self.rubrique_obj.create(r12_data)
        r12.should_be_done()
        #R13
        r13_data = dict(static_data, date_start="2016-05-03", date_end="2016-10-31", name='YES')
        r13 = self.rubrique_obj.create(r13_data)
        r13.should_be_done()
        #R14
        r14_data = dict(static_data, date_start="2016-05-03", date_end="2016-12-09", name='YES')
        r14 = self.rubrique_obj.create(r14_data)
        r14.should_be_done()
        #r15
        r15_data = dict(static_data, date_start="2016-10-01", date_end="2016-10-09", name='YES')
        r15 = self.rubrique_obj.create(r15_data)
        r15.should_be_done()
        #r16
        r16_data = dict(static_data, date_start="2016-10-01", date_end="2016-10-31", name='YES')
        r16 = self.rubrique_obj.create(r16_data)
        r16.should_be_done()
        #r17
        r17_data = dict(static_data, date_start="2016-10-17", date_end="2016-10-31", name='YES')
        r17 = self.rubrique_obj.create(r17_data)
        r17.should_be_done()
        #r18
        r18_data = dict(static_data, date_start="2016-10-17", date_end="2016-10-20", name='YES')
        r18 = self.rubrique_obj.create(r18_data)
        r18.should_be_done()
        #r19
        r19_data = dict(static_data, date_start="2016-10-17", date_end="2016-11-20", name='YES')
        r19 = self.rubrique_obj.create(r19_data)
        r19.should_be_done()
        #r20
        r20_data = dict(static_data, date_start="2016-10-31", date_end="2016-11-20", name='YES')
        r20 = self.rubrique_obj.create(r20_data)
        r20.should_be_done()
        #r21
        r21_data = dict(static_data, date_start="2016-11-01", date_end="2016-11-20", name='NO')
        r21 = self.rubrique_obj.create(r21_data)
        r21.should_be_done()
        #r22
        r22_data = dict(static_data, date_start="2016-11-20", date_end="2017-11-20", name='NO')
        r22 = self.rubrique_obj.create(r22_data)
        r22.should_be_done()
        #End creating
        all_rubriques = self.rubrique_obj.search([('employee_id','=',self.emp.id)])
        passed_rubriques = self.rubrique_obj.search(self.rubrique_obj.get_domain(
            employee_id=self.emp.id,
            code=self.code,
            state='done',
            date_start='2016-10-01',
            date_end='2016-10-31',
        ))
        passes = passed_rubriques.mapped('name')
        nos = (all_rubriques.filtered(lambda r: r not in passed_rubriques)).mapped('name')
        self.assertEqual(len(all_rubriques), 22, 'Number of rubriques is 22')
        self.assertEqual(list(set(passes)), ['YES'], 'All passes should be YES')
        self.assertEqual(list(set(nos)), ['NO'], 'All nos should be NO')
