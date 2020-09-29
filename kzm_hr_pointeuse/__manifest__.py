# -*- coding: utf-8 -*-
{
    'name': "DB: KZM Gestion de Pointeuses",

    'summary': """
        Gestion des pointeuses & présences & badges """,

    'description': """
        Le module permet une gestion maitrisée des pointeuses. L'utilisateur pourra réaliser tous les opérations d'ajout, modification et suppression d'une pointeuse.
        Le module permet en outre de tester si une pointeuse est connectée ou pas.
        il permet aussi l'import automatiques des présences à partir des pointeuses gérées
        il permet aussi la gestion des badges, leur impression et la communication avec les pointeuses, (gestion des utilisateurs, des badges, ...)
    """,

    'author': "Abdelmajid Elhamdaoui, Karizma-conseil",
    'website': "http://www.karizma-conseil.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Modules & Communication',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'hr_attendance',
        'hr_contract',
        'kzm_hr_contract_type'
    ],

    # always loaded
    'data': [

        'data/kzm_hr_pointeuse_data.xml',
        'data/kzm_hr_employee_sequence.xml',
        'data/kzm_hr_pointeuse_sequence.xml',
        'data/paperFormat.xml',
        'data/crons.xml',

        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'kzm_hr_pointage_journalier/security/kzm_security.xml',
        'kzm_hr_pointage_journalier/security/ir.model.access.csv',
        'kzm_hr_pointage_journalier/security/ir_rule.xml',

        'wizard/wizard_finalize_attendencies.xml',

        'kzm_hr_pointage_journalier/kzm_hr_pointage_journalier.xml',
        'kzm_hr_pointage_journalier/kzm_sequence.xml',
        'kzm_hr_pointage_journalier/kzm_statistique_view.xml',
        'kzm_hr_pointage_journalier/hr_employee_view.xml',
        'kzm_hr_pointage_journalier/kzm_presences_journalieres.xml',
        
        'views/kzm_hr_pointeuse_view.xml',
        'views/kzm_hr_pointeuse_badge_view.xml',
        'views/kzm_hr_pointeuse_badge_report.xml',
        'views/zk_attendencies.xml',
        'views/kzm_import_attendance_view.xml',
        'views/hr_attendance_view.xml',
        'views/specific_holidays.xml',
        'views/menus.xml',

        'wizard/kzm_hr_pointeuse_connection_view.xml',
        'wizard/kzm_hr_pointeuse_load_attendance_view.xml',
        'wizard/kzm_hr_pointeuse_copie.xml',

        



    ],
    # only loaded in demonstration mode
    'demo': [

    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
