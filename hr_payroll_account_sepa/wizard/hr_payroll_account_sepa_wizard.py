# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslipSepaWizard(models.TransientModel):
    _name = 'hr.payslip.sepa.wizard'
    _description = 'HR Payslip SEPA Wizard'

    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))

    def generate_sepa_xml_file(self):
        self = self.with_context(skip_bic=True)
        payslips = self.env['hr.payslip'].browse(self.env.context['active_ids'])
        payslips = payslips.filtered(lambda p: p.net_wage > 0)
        invalid_employees = payslips.mapped('employee_id').filtered(lambda e: e.bank_account_id.acc_type != 'iban')
        if invalid_employees:
            raise UserError(_('Invalid bank account for the following employees:\n%s', '\n'.join(invalid_employees.mapped('name'))))
        payslips.sudo()._create_xml_file(self.journal_id)


class HrPayslipRunSepaWizard(models.TransientModel):
    _name = 'hr.payslip.run.sepa.wizard'
    _description = 'HR Payslip Run SEPA Wizard'

    def _get_filename(self):
        payslip_run_id = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        return payslip_run_id.sepa_export_filename or payslip_run_id.name

    journal_id = fields.Many2one(
        string='Bank Journal', comodel_name='account.journal', required=True,
        default=lambda self: self.env['account.journal'].search([('type', '=', 'bank')], limit=1))
    file_name = fields.Char(string='File name', required=True, default=_get_filename)

    def generate_sepa_xml_file(self):
        self = self.with_context(skip_bic=True)
        payslip_run = self.env['hr.payslip.run'].browse(self.env.context['active_id'])
        payslips = payslip_run.mapped('slip_ids').filtered(lambda p: p.net_wage > 0)
        invalid_employees = payslips.mapped('employee_id').filtered(lambda e: e.bank_account_id.acc_type != 'iban')
        if invalid_employees:
            raise UserError(_('Invalid bank account for the following employees:\n%s', '\n'.join(invalid_employees.mapped('name'))))
        payslips.sudo()._create_xml_file(self.journal_id, self.file_name)
