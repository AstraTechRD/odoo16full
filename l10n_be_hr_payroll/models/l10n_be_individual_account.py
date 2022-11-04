# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging

from collections import OrderedDict
from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nBeIndividualAccount(models.Model):
    _name = 'l10n_be.individual.account'
    _description = 'HR Individual Account Report By Employee'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    def _get_selection(self):
        current_year = datetime.datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 1)]

    year = fields.Selection(
        selection='_get_selection', string='Year', required=True,
        default=lambda x: str(datetime.datetime.now().year - 1))
    name = fields.Char(
        string="Description", required=True, compute='_compute_name', readonly=False, store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    line_ids = fields.One2many(
        'l10n_be.individual.account.line', 'sheet_id', compute='_compute_line_ids', store=True, readonly=False)

    @api.depends('year')
    def _compute_name(self):
        for sheet in self:
            sheet.name = _('Individual Accounts - Year %s', sheet.year)

    @api.depends('year', 'company_id')
    def _compute_line_ids(self):
        for sheet in self:
            all_payslips = self.env['hr.payslip'].search([
                ('date_to', '<=', datetime.date(int(sheet.year), 12, 31)),
                ('date_from', '>=', datetime.date(int(sheet.year), 1, 1)),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', sheet.company_id.id),
            ])
            all_employees = all_payslips.mapped('employee_id')
            sheet.write({
                'line_ids': [(5, 0, 0)] + [(0, 0, {
                    'employee_id': employee.id,
                }) for employee in all_employees]
            })

    def _get_rendering_data(self, employees):
        self.ensure_one()

        payslips = self.env['hr.payslip'].search([
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['done', 'paid']),
            ('date_from', '>=', Datetime.now().replace(month=1, day=1, year=int(self.year))),
            ('date_from', '<=', Datetime.now().replace(month=12, day=31, year=int(self.year))),
            '|',
            ('struct_id.country_id', '=', False),
            ('struct_id.country_id.code', '=', "BE"),
        ])
        employees = payslips.employee_id
        lines = payslips.line_ids.filtered(lambda l: l.salary_rule_id.appears_on_payslip)
        payslip_rules = [(rule.code, rule.sequence) for rule in lines.salary_rule_id]
        payslip_rules = sorted(payslip_rules, key=lambda x: x[1])
        worked_days = payslips.worked_days_line_ids

        result = {
            employee: {
                'rules': OrderedDict(
                    (rule[0], {
                        'year': {'name': False, 'total': 0},
                        'month': {m: {'name': False, 'total': 0} for m in range(12)},
                        'quarter': {q: {'name': False, 'total': 0} for q in range(4)}
                    }) for rule in payslip_rules),
                'worked_days': {
                    code: {
                        'year': {'name': False, 'number_of_days': 0, 'number_of_hours': 0},
                        'month': {m: {'name': False, 'number_of_days': 0, 'number_of_hours': 0} for m in range(12)},
                        'quarter': {q: {'name': False, 'number_of_days': 0, 'number_of_hours': 0} for q in range(4)}
                    } for code in worked_days.mapped('code')
                }
            } for employee in employees
        }

        for line in lines:
            rule = result[line.employee_id]['rules'][line.salary_rule_id.code]
            month = line.slip_id.date_from.month - 1
            rule['month'][month]['name'] = line.name
            rule['month'][month]['total'] += line.total
            rule['quarter'][(month) // 3]['name'] = line.name
            rule['quarter'][(month) // 3]['total'] += line.total
            rule['year']['name'] = line.name
            rule['year']['total'] += line.total

            rule['month'][month]['total'] = round(rule['month'][month]['total'], 2)
            rule['quarter'][(month) // 3]['total'] = round(rule['quarter'][(month) // 3]['total'], 2)
            rule['year']['total'] = round(rule['year']['total'], 2)

        for worked_day in worked_days:
            work = result[worked_day.payslip_id.employee_id]['worked_days'][worked_day.code]
            month = worked_day.payslip_id.date_from.month - 1

            work['month'][month]['name'] = worked_day.name
            work['month'][month]['number_of_days'] += worked_day.number_of_days
            work['month'][month]['number_of_hours'] += worked_day.number_of_hours
            work['quarter'][(month) // 3]['name'] = worked_day.name
            work['quarter'][(month) // 3]['number_of_days'] += worked_day.number_of_days
            work['quarter'][(month) // 3]['number_of_hours'] += worked_day.number_of_hours
            work['year']['name'] = worked_day.name
            work['year']['number_of_days'] += worked_day.number_of_days
            work['year']['number_of_hours'] += worked_day.number_of_hours

        return result

    def action_generate_pdf(self):
        self.line_ids.write({'pdf_to_generate': True})
        self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()

    def _process_files(self, files):
        self.ensure_one()
        for employee, filename, data in files:
            line = self.line_ids.filtered(lambda l: l.employee_id == employee)
            line.write({
                'pdf_file': base64.encodebytes(data),
                'pdf_filename': filename,
            })


class L10nBeIndividualAccountLine(models.Model):
    _name = 'l10n_be.individual.account.line'
    _description = 'HR Individual Account Report By Employee Line'

    employee_id = fields.Many2one('hr.employee')
    pdf_file = fields.Binary('PDF File', readonly=True, attachment=False)
    pdf_filename = fields.Char()
    sheet_id = fields.Many2one('l10n_be.individual.account')
    pdf_to_generate = fields.Boolean()

    def _generate_pdf(self):
        report_sudo = self.env["ir.actions.report"].sudo()
        report_id = self.env.ref('l10n_be_hr_payroll.action_report_individual_account').id

        for sheet in self.sheet_id:
            lines = self.filtered(lambda l: l.sheet_id == sheet)
            rendering_data = sheet._get_rendering_data(lines.employee_id)

            pdf_files = []
            sheet_count = len(rendering_data)
            counter = 1
            for employee, employee_data in rendering_data.items():
                _logger.info('Printing Individual Account sheet (%s/%s)', counter, sheet_count)
                counter += 1
                employee_lang = employee.sudo().address_home_id.lang
                sheet_filename = _('%s-individual-account-%s', employee.name, sheet.year)
                sheet_file, dummy = report_sudo.with_context(lang=employee_lang)._render_qweb_pdf(
                    report_id,
                    [employee.id], data={
                        'year': int(sheet.year),
                        'employee_data': {employee: employee_data}})
                pdf_files.append((employee, sheet_filename, sheet_file))
            if pdf_files:
                sheet._process_files(pdf_files)
