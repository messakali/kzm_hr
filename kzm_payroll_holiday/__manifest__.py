# -*- coding: utf-8 -*-
{
    'name': "Kzm Payroll Holiday",

    'summary': """
        Payroll Holiday""",

    'description': """
        
    """,

    'author': "karizma",
    'website': "http://www.karizma.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr_holidays', 'kzm_payroll_ma'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [

    ],
}