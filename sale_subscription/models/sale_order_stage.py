# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderStage(models.Model):
    _name = 'sale.order.stage'
    _description = 'Sale Order Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text("Requirements", help="Enter here the internal requirements for this stage. It will appear as a tooltip over the stage's name.", translate=True)
    sequence = fields.Integer(default=1)
    fold = fields.Boolean(string='Folded in Kanban', help='This stage is folded in the kanban view when there are no records in that stage to display.')
    rating_template_id = fields.Many2one('mail.template', string='Rating Email Template',
                                         help="Send an email to the customer when the subscription is moved to this stage.",
                                         domain=[('model', '=', 'sale.order')])
    category = fields.Selection([('draft', 'Quotation'), ('progress', 'In Progress'), ('paused', 'Invoicing Pause'), ('closed', 'Closed')],
                                required=True, default='draft')
