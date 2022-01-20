# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'COA Invoice Button',
    'version': '1.0.1',
    'category': 'Account',
    'sequence': 20,
    'summary': 'Add button for displaying invoices',
    'description': "",
    'depends': ['base','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account.xml',
        'views/account_move.xml',
        'wizard/account_move_writeoff_view.xml'
    ],
    'demo': [

    ],
    'installable': True,
    'application': True,
    'website': '',
}
