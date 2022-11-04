# coding: utf-8
from odoo import fields, models


class ProductUom(models.Model):
    _inherit = 'uom.uom'

    l10n_co_edi_ubl = fields.Char(string=u'Código UBL')
    l10n_co_edi_country_code = fields.Char(default=lambda self: self.env.company.country_id.code)
