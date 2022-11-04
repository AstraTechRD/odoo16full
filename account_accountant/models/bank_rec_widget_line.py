# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, Command

import uuid


class BankRecWidgetLine(models.Model):
    _name = "bank.rec.widget.line"
    _inherit = "analytic.mixin"
    _description = "Line of the lines_widget"

    # This model is never saved inside the database.
    # _auto=False' & _table_query = "0" prevent the ORM to create the corresponding postgresql table.
    _auto = False
    _table_query = "0"

    wizard_id = fields.Many2one(comodel_name='bank.rec.widget')
    index = fields.Char(compute='_compute_index')
    flag = fields.Selection(
        selection=[
            ('liquidity', 'liquidity'),
            ('new_aml', 'new_aml'),
            ('aml', 'aml'),
            ('tax_line', 'tax_line'),
            ('manual', 'manual'),
            ('early_payment', 'early_payment'),
            ('auto_balance', 'auto_balance'),
        ],
    )

    account_id = fields.Many2one(
        comodel_name='account.account',
        compute='_compute_account_id',
        store=True,
        readonly=False,
    )
    date = fields.Date(
        compute='_compute_date',
        store=True,
        readonly=False,
    )
    name = fields.Char(
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_compute_partner_id',
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True,
        readonly=False,
    )
    company_currency_id = fields.Many2one(related='wizard_id.company_currency_id')
    amount_currency = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_amount_currency',
        store=True,
        readonly=False,
    )
    balance = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_balance',
        store=True,
        readonly=False,
    )
    debit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_balance',
    )
    credit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_balance',
    )
    force_price_included_taxes = fields.Boolean(
        compute='_compute_force_price_included_taxes',
        readonly=False,
        store=True,
    )
    tax_base_amount_currency = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_tax_base_amount_currency',
        readonly=False,
        store=True,
    )

    source_aml_id = fields.Many2one(comodel_name='account.move.line')
    source_aml_move_id = fields.Many2one(
        comodel_name='account.move',
        compute='_compute_source_aml_fields',
        store=True,
        readonly=False,
    )
    source_aml_move_name = fields.Char(
        compute='_compute_source_aml_fields',
        store=True,
        readonly=False,
    )
    tax_repartition_line_id = fields.Many2one(
        comodel_name='account.tax.repartition.line',
        compute='_compute_tax_repartition_line_id',
        store=True,
        readonly=False,
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        compute='_compute_tax_ids',
        store=True,
        readonly=False,
    )
    tax_tag_ids = fields.Many2many(
        comodel_name='account.account.tag',
        compute='_compute_tax_tag_ids',
        store=True,
        readonly=False,
    )
    group_tax_id = fields.Many2one(
        comodel_name='account.tax',
        compute='_compute_group_tax_id',
        store=True,
        readonly=False,
    )
    reconcile_model_id = fields.Many2one(comodel_name='account.reconcile.model')
    source_amount_currency = fields.Monetary(currency_field='currency_id')
    source_balance = fields.Monetary(currency_field='company_currency_id')
    source_debit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_source_balance',
    )
    source_credit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_source_balance',
    )

    display_stroked_amount_currency = fields.Boolean(compute='_compute_display_stroked_amount_currency')
    display_stroked_balance = fields.Boolean(compute='_compute_display_stroked_balance')

    def _compute_index(self):
        for line in self:
            line.index = uuid.uuid4()

    @api.depends('source_aml_id')
    def _compute_account_id(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'liquidity'):
                line.account_id = line.source_aml_id.account_id

    @api.depends('source_aml_id')
    def _compute_date(self):
        for line in self:
            if line.flag in ('aml', 'new_aml'):
                line.date = line.source_aml_id.date
            elif line.flag in ('liquidity', 'auto_balance', 'manual', 'early_payment', 'tax_line'):
                line.date = line.wizard_id.st_line_id.date

    @api.depends('source_aml_id')
    def _compute_name(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'liquidity'):
                line.name = line.source_aml_id.name

    @api.depends('source_aml_id')
    def _compute_partner_id(self):
        for line in self:
            if line.flag in ('aml', 'new_aml'):
                line.partner_id = line.source_aml_id.partner_id
            elif line.flag in ('liquidity', 'auto_balance', 'manual', 'early_payment', 'tax_line'):
                line.partner_id = line.wizard_id.partner_id

    @api.depends('source_aml_id')
    def _compute_currency_id(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'liquidity'):
                line.currency_id = line.source_aml_id.currency_id
            elif line.flag in ('auto_balance', 'manual', 'early_payment'):
                line.currency_id = line.wizard_id.transaction_currency_id

    @api.depends('source_aml_id')
    def _compute_balance(self):
        for line in self:
            if line.flag in ('aml', 'liquidity'):
                line.balance = line.source_aml_id.balance

    @api.depends('source_aml_id')
    def _compute_amount_currency(self):
        for line in self:
            if line.flag in ('aml', 'liquidity'):
                line.amount_currency = line.source_aml_id.amount_currency

    @api.depends('balance')
    def _compute_from_balance(self):
        for line in self:
            line.debit = line.balance if line.balance > 0.0 else 0.0
            line.credit = -line.balance if line.balance < 0.0 else 0.0

    @api.depends('source_balance')
    def _compute_from_source_balance(self):
        for line in self:
            line.source_debit = line.source_balance if line.source_balance > 0.0 else 0.0
            line.source_credit = -line.source_balance if line.source_balance < 0.0 else 0.0

    @api.depends('source_aml_id')
    def _compute_analytic_distribution(self):
        for line in self:
            if line.flag in ('aml', 'new_aml'):
                line.analytic_distribution = line.source_aml_id.analytic_distribution

    @api.depends('source_aml_id')
    def _compute_tax_repartition_line_id(self):
        for line in self:
            if line.flag == 'aml':
                line.tax_repartition_line_id = line.source_aml_id.tax_repartition_line_id

    @api.depends('source_aml_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.flag == 'aml':
                line.tax_ids = [Command.set(line.source_aml_id.tax_ids.ids)]

    @api.depends('source_aml_id')
    def _compute_tax_tag_ids(self):
        for line in self:
            if line.flag == 'aml':
                line.tax_tag_ids = [Command.set(line.source_aml_id.tax_tag_ids.ids)]

    @api.depends('source_aml_id')
    def _compute_group_tax_id(self):
        for line in self:
            if line.flag == 'aml':
                line.group_tax_id = line.source_aml_id.group_tax_id

    @api.depends('currency_id', 'amount_currency', 'source_amount_currency')
    def _compute_display_stroked_amount_currency(self):
        for line in self:
            line.display_stroked_amount_currency = \
                line.flag == 'new_aml' \
                and line.currency_id.compare_amounts(line.amount_currency, line.source_amount_currency) != 0

    @api.depends('currency_id', 'balance', 'source_balance')
    def _compute_display_stroked_balance(self):
        for line in self:
            line.display_stroked_balance = \
                line.flag == 'new_aml' \
                and line.currency_id.compare_amounts(line.balance, line.source_balance) != 0

    @api.depends('tax_ids')
    def _compute_force_price_included_taxes(self):
        for line in self:
            line.force_price_included_taxes = bool(line.tax_ids)

    @api.depends('force_price_included_taxes', 'amount_currency')
    def _compute_tax_base_amount_currency(self):
        for line in self:
            if line.force_price_included_taxes:
                line.tax_base_amount_currency = line.tax_base_amount_currency
            else:
                line.tax_base_amount_currency = line.amount_currency

    @api.depends('flag')
    def _compute_source_aml_fields(self):
        for line in self:
            line.source_aml_move_id = None
            line.source_aml_move_name = None
            if line.flag in ('new_aml', 'liquidity'):
                line.source_aml_move_id = line.source_aml_id.move_id
                line.source_aml_move_name = line.source_aml_id.move_id.name
            elif line.flag == 'aml':
                partials = line.source_aml_id.matched_debit_ids + line.source_aml_id.matched_credit_ids
                all_counterpart_lines = partials.debit_move_id + partials.credit_move_id
                counterpart_lines = all_counterpart_lines - line.source_aml_id - partials.exchange_move_id.line_ids
                if len(counterpart_lines) == 1:
                    line.source_aml_move_id = counterpart_lines.move_id
                    line.source_aml_move_name = counterpart_lines.move_id.name
