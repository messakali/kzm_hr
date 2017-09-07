# encoding: utf-8

{
    'name': 'Paie marocaine - Simpl-IR',
    'version': '1.0.0',
    'author': 'Karizma',
    'category': 'Paie marocaine',
    'summary': 'Télédéclaration Simpl-IR',
    'description' : """
Paie marocaine - Simpl-IR
=========================

    """,
    'website': 'http://www.kzarizma.ma',
    'images': [],
    'depends': ['l10n_ma_hr_payroll_damancom'],
    'data': [
        'security/hr.xml',
        'views/teledeclaration_salary.xml',
        'security/ir.model.access.csv',
    ],
    "qweb": [

    ],
    'demo': [

    ],
    'test': [

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
