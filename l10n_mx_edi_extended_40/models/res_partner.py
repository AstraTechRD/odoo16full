# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_edi_external_trade_type = fields.Selection(
        selection=[
            ('02', 'Definitive'),
            ('03', 'Temporary'),
        ],
        string='External Trade',
        help="Indicates whether the partner is foreign and if a External Trade complement is required"
             "Not Set: No Complement"
             "02 - Definitive: Adds the External Trade complement to CFDI"
             "03 - Temporal: Used when exporting goods for a temporary period")
