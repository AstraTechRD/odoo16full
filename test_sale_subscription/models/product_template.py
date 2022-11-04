# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProductTemplateTest(models.Model):
    """ A model inheriting from product.template with some fields and override used in test """
    _inherit = "product.template"

    incompatible_checkbox = fields.Boolean('Incompatible checkbox',
                                           help='If set, on a subscription product, a python constraint will be raised')

    @api.model
    def _get_incompatible_types(self):
        return ['incompatible_checkbox'] + super()._get_incompatible_types()

    @api.constrains('incompatible_checkbox')
    def _prevent_test_subscription_incompatibility(self):
        """ Some boolean fields are incompatibles """
        self._check_incompatible_types()
