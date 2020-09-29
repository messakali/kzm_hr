# -*- coding: utf-8 -*-
{
    'name': "Pointage journalier",

    'summary': """
        Gestion du pointage journalier des employées """,

    'description': """
        Le module permet une gestion maitrisée des pointages journalier en ce basant sur le module pointeuse pour générer le pointage automatique
        et permet au utilisateur d'inserer le pointage manuel des heures normales et des heures sup    """,

    'author': "Abdelmajid ELhamdaoui, KARIZMA CONSEIL",
    'website': "http://www.karizma.ma",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Modules & Communication',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['kzm_hr_pointeuse'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/kzm_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'kzm_hr_pointage_journalier.xml',
        'kzm_sequence.xml',
        'kzm_statistique_view.xml',
        'hr_employee_view.xml',
        'kzm_presences_journalieres.xml',
    ],
    # only loaded in demonstration mode
    'demo': [

    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}