# -*- coding: utf-8 -*-
{
    'name': 'KZM HR Pointeuse Client',
    'version': '13.0',
    'category': 'HR',
    'complexity': "normal",
    'description': """
                    Module qui gére la pointeuse
                   """,
    'author': 'KARIZMA CONSEIL',
    'website': 'https://karizma-conseil.com',
    'images': [],
    'depends': ['base','kzm_hr_pointeuse'],
    'data': [
        'security/security_view.xml',
        # 'security/ir.model.access.csv',
        'views/res_config.xml',
        'views/kzm_hr_pointeuse.xml',

    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}

