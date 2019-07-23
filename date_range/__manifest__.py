# -*- coding: utf-8 -*-

{
    "name": "Date Range",
    "summary": "Manage all kind of date range",
    "version": "10.0",
    "category": "Uncategorized",
    "author": "Andema",
    "website": "https://andemaconsulting.com/",
    "application": False,
    "installable": True,
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/date_range_security.xml",
        "views/assets.xml",
        "views/date_range_view.xml",
        "wizard/date_range_generator.xml",
    ],
    "qweb": [
        "static/src/xml/date_range.xml",
    ]
}
