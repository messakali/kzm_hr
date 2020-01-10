# -*- coding: utf-8 -*-
{
    'name': 'Etat 9421',
    'version': '11.0',
    'category': 'HR',
    'complexity': "normal",
    'description': """
                    Module qui génère l'état 9421
                   """,
    'author': 'KARIZMA CONSEIL',
    'website': 'https://karizma-conseil.com',
    'images': [],
    'depends': ['kzm_payroll_ma', 'kzm_base', 'kzm_hr_contract_type'],
    'data': [
            "data/payroll_data.xml",
            "security/security_view.xml",
            "security/ir.model.access.csv",
            'views/etat_9421_view.xml',
            # 'views/res_partner_view.xml',
            #'views/hr_payroll_view.xml',
            'views/hr_employee_view.xml',
            'report/reports_view.xml',
            'report/etat_ir.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}

