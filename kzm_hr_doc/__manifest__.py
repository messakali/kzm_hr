# encoding: utf-8

{
    'name': 'Gestion des doc',
    'version': '4.0.0',
    'author': 'Karizma Conseil',
    'website': "http://www.karizma.ma",
    'category': 'DOC',
    'summary': 'Gestion des doc',
    'description' : """
=====================================

    """,
    'images': [],
    'depends': ['l10n_ma_hr_payroll'],
    'data': [
        'security/rule.xml',
        'security/ir.model.access.csv',
        'workflow/document_wkf.xml',
        'workflow/warning_wkf.xml',
        'data/document.xml',
        'data/warning.xml',
        'views/document.xml',
        'views/warning.xml',
        'views/employee.xml',
        'report/report_warning.xml',
        'report/report.xml',
    ],
    "qweb": [

    ],
    'demo': [

    ],
    'test': [

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
