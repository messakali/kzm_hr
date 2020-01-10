# -*- coding: utf-8 -*-
{
    'name': u'Télédéclaration CNSS',
    'version': '11.0',
    'category': 'hr',
    'description': u"Télédéclaration CNSS",
    'author': 'KARIZMA CONSEIL',
    'website': 'https://karizma-conseil.com',
    'depends': ["kzm_payroll_ma"],
    'data': [
                "security/security_view.xml",
                "security/ir.model.access.csv",
                'wizard/e_bds_wizard_view.xml',
                'views/e_bds_view.xml'
    ],

    'installable': True,
    'active': False,
}

