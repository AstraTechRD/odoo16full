# coding: utf-8

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # == Addenda ==
    l10n_mx_edi_addenda = fields.Many2one(
        comodel_name='ir.ui.view',
        string="Addenda",
        help="A view representing the addenda",
        domain=[('l10n_mx_edi_addenda_flag', '=', True)])
    l10n_mx_edi_addenda_doc = fields.Html(
        string="Addenda Documentation",
        help="How should be done the addenda for this customer (try to put human readable information here to help the "
             "invoice people to fill properly the fields in the invoice)")
