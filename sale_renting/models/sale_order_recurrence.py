# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class SaleOrderRecurrence(models.Model):
    _inherit = 'sale.temporal.recurrence'

    unit = fields.Selection(selection_add=[('hour', 'Hours')], ondelete={'hour': lambda sor: sor.write({'unit': 'day'})})
