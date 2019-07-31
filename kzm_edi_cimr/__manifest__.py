# -*- coding: utf-8 -*-
{
    'name': u'Télédéclaration CIMR',
    'version': '11.0',
    'category': 'HR',
    'complexity': "normal",
    'description': """Télédéclaration CIMR """,
    'author': 'KARIZMA CONSEIL',
    'website': 'https://karizma-conseil.com',
    'images': [],
    'depends': ['kzm_payroll_ma'],
    'data': [
            "security/cimr_security.xml",
            "security/ir.model.access.csv",
            "wizard/teledeclaration_cimr_view.xml",
            'report/reports_view.xml',
            'report/etat_cimr.xml',
            'views/hr_employe_view.xml',
            'views/company_view.xml',
            'views/rapport_cimr_view.xml',
            'views/cimr_employee_sortant_view.xml'
    ],
    'demo': [ ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}

