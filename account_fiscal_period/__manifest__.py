# -*- coding: utf-8 -*-

{
    'name': 'Account Fiscal Period',
    'version': '10.0',
    'category': 'Accounting',
    'author': 'Andeùa',
    'website': 'http://www.andemaconsulting.com',
    'depends': [
        'account_fiscal_year',
    ],
    'data': [
        'security/date_range_security.xml',
        'security/ir.model.access.csv',
        'data/date_range_type.xml',
        'views/date_range_type.xml',
        'views/date_range.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
