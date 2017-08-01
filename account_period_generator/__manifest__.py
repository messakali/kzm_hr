# -*- coding: utf-8 -*-
# Author: Reda Rouichi
# Copyright 2017 KARIZMA CONSEIL
{
    'name': 'Account Period Generator',
    'version': '10.0.1.0.0',
    'category': 'Accounting',
    'author': 'KARIZMA CONSEIL',
    'website': 'http://www.karizma.ma',
    'depends': [
        'account_fiscal_year'
    ],
    'data': [
        'data/date_range_type.xml',
        'views/date_range_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
