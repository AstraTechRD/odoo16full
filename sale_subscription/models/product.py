# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class product_template(models.Model):
    _inherit = "product.template"

    recurring_invoice = fields.Boolean(
        'Subscription Product',
        help='If set, confirming a sale order with this product will create a subscription')

    @api.model
    def _get_incompatible_types(self):
        return ['recurring_invoice'] + super()._get_incompatible_types()

    @api.constrains('recurring_invoice')
    def _prevent_subscription_incompability(self):
        """ Some boolean fields are incompatibles """
        self._check_incompatible_types()

    @api.depends('recurring_invoice')
    def _compute_is_temporal(self):
        super()._compute_is_temporal()
        self.filtered('recurring_invoice').is_temporal = True

    @api.onchange('type')
    def _onchange_product_type(self):
        """
        Raise a warning if the user has selected 'Storable Product'
        while the product has already been set as a 'Subscription Product'.
        In this case, the 'type' field is reset.
        """
        if self.type == 'product' and self.recurring_invoice:
            self.type = False
            return {'warning': {
                'title': _("Warning"),
                'message': _("A 'Subscription Product' cannot be a 'Storable Product' !")
            }}

    @api.onchange('recurring_invoice')
    def _onchange_recurring_invoice(self):
        """
        Raise a warning if the user has checked 'Subscription Product'
        while the product has already been set as a 'Storable Product'.
        In this case, the 'Subscription Product' field is automatically
        unchecked.
        """
        if self.type == 'product' and self.recurring_invoice:
            self.recurring_invoice = False
            return {'warning': {
                'title': _("Warning"),
                'message': _("A 'Storable Product' cannot be a 'Subscription Product' !")
            }}
