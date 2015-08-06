#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
{
    "name" : "natuurpunt_coda",
    "version" : "1.0",
    "author" : "SmartSolution",
    "category" : "Generic Modules/Base",
    "description": """
""",
    "depends" : ["base","account","multi_analytical_account","l10n_be_coda"],
    "update_xml" : [
        'natuurpunt_coda_view.xml',
        'security/natuurpunt_coda_security.xml',
        'security/ir.model.access.csv'
        ],
    "active": False,
    "installable": True
}
