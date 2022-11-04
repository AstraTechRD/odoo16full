# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

def post_init(cr, registry):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['project.project'].search([('is_fsm', '=', True)]).write({
        'allow_billable': True,
        'allow_material': True,
        'allow_timesheets': True,
        'timesheet_product_id': env.ref('sale_timesheet.time_product')
    })
