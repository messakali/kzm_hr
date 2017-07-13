# encoding: utf-8

{
    'name': 'Paie marocaine - DAMANCOM',
    'version': '1.0.0',
    'author': 'Karizma',
    'category': 'Paie marocaine',
    'summary': 'Télédéclaration DAMANCOM',
    'description' : """
Paie marocaine - DAMANCOM
=========================

    """,
    'website': 'http://www.karizma.ma',
    'images': [],
    'depends': ['l10n_ma_hr_payroll'],
    'data': [
        'security/hr.xml',
        'security/ir.model.access.csv',
        'views/contract.xml',
        'views/employee.xml',
        'wizard/teledeclaration_damancom.xml',
        'wizard/contract.xml',
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
