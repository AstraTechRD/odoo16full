# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountAccount(models.Model):
    _inherit = 'account.account'

    asset_model = fields.Many2one(
        'account.asset',
        domain=lambda self: [('state', '=', 'model'), ('asset_type', '=', self.asset_type)],
        help="If this is selected, an expense/revenue will be created automatically "
             "when Journal Items on this account are posted.",
        tracking=True)
    create_asset = fields.Selection([('no', 'No'), ('draft', 'Create in draft'), ('validate', 'Create and validate')],
                                    required=True, default='no', tracking=True)
    # specify if the account can generate asset depending on it's type. It is used in the account form view
    can_create_asset = fields.Boolean(compute="_compute_can_create_asset")
    form_view_ref = fields.Char(compute='_compute_can_create_asset')
    asset_type = fields.Selection([('sale', 'Deferred Revenue'), ('expense', 'Deferred Expense'), ('purchase', 'Asset')], compute='_compute_can_create_asset')
    # decimal quantities are not supported, quantities are rounded to the lower int
    multiple_assets_per_line = fields.Boolean(string='Multiple Assets per Line', default=False, tracking=True,
        help="Multiple asset items will be generated depending on the bill line quantity instead of 1 global asset.")

    @api.depends('account_type')
    def _compute_can_create_asset(self):
        for record in self:
            if record.auto_generate_asset():
                record.asset_type = 'purchase'
            elif record.auto_generate_deferred_revenue():
                record.asset_type = 'sale'
            elif record.auto_generate_deferred_expense():
                record.asset_type = 'expense'
            else:
                record.asset_type = False

            record.can_create_asset = record.asset_type != False

            record.form_view_ref = {
                'purchase': 'account_asset.view_account_asset_form',
                'sale': 'account_asset.view_account_asset_revenue_form',
                'expense': 'account_asset.view_account_asset_expense_form',
            }.get(record.asset_type)

    @api.onchange('create_asset')
    def _onchange_multiple_assets_per_line(self):
        for record in self:
            if record.create_asset == 'no':
                record.multiple_assets_per_line = False

    def auto_generate_asset(self):
        return self.account_type in ('asset_fixed', 'asset_non_current')

    def auto_generate_deferred_revenue(self):
        return self.account_type in ('liability_non_current', 'liability_current')

    def auto_generate_deferred_expense(self):
        return self.account_type in ('asset_prepayments', 'asset_current')
