# -*- coding: utf-8 -*-

{
    'name': "Purchase partial invoicing",
    'version': '0.1',
    'category': 'Purchase Management',
    'description': """
This module allows to partially invoice purchase order lines.
The 'Create invoices' from PO lines wizard allows to specify,
for each line, the quantity to invoice.
""",
    'author': '',
    'website': '',
    'license': '',
    "depends": ['natuurpunt_purchase_approval_ext'],
    "data": [
        'wizard/po_line_invoice_view.xml',
        'purchase_view.xml',
    ],
    "demo": [],
    "active": False,
    "installable": True,
}
