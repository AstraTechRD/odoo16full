# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_ke_mortgage_interest = fields.Monetary("Mortgage Interest")
    l10n_ke_pension_contribution = fields.Monetary("Pension Contribution")
    l10n_ke_insurance_relief = fields.Monetary("Insurance Relief")

    @api.constrains('l10n_ke_mortgage_interest')
    def _check_l10n_ke_mortgage_interest(self):
        max_amount = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('l10n_ke_max_mortgage_interest', raise_if_not_found=False)
        for contract in self:
            if max_amount and contract.l10n_ke_mortgage_interest > max_amount:
                raise ValidationError(_('The mortgage interest cannot exceed %s Ksh!', max_amount))

    @api.constrains('l10n_ke_pension_contribution')
    def _check_l10n_ke_pension_contribution(self):
        max_amount = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('l10n_ke_max_pension_contribution', raise_if_not_found=False)
        for contract in self:
            if max_amount and contract.l10n_ke_pension_contribution > max_amount:
                raise ValidationError(_('The pension contribution cannot exceed %s Ksh!', max_amount))

    @api.constrains('l10n_ke_insurance_relief')
    def _check_l10n_ke_insurance_relief(self):
        max_amount = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('l10n_ke_max_insurance_relief', raise_if_not_found=False)
        for contract in self:
            if max_amount and contract.l10n_ke_insurance_relief > max_amount:
                raise ValidationError(_('The insurance relief cannot exceed %s Ksh!', max_amount))
