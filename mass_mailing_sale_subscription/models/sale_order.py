# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression

class SaleOrder(models.Model):
    _inherit = "sale.order"
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        domain = super()._mailing_get_default_domain(mailing)
        return expression.AND([domain, [('stage_category', '=', 'progress')]])

    def _sms_get_number_fields(self):
        """ No phone or mobile field is available on subscription model. Instead
        SMS will fallback on partner-based computation using ``_sms_get_partner_fields``. """
        return []

    def _sms_get_partner_fields(self):
        return ['partner_id']
