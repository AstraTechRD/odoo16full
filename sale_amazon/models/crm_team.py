# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    amazon_team = fields.Boolean(
        help="Whether this sales team is associated with Amazon orders or not."
    )
