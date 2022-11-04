#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ContributionRegisterReport(models.AbstractModel):
    _name = 'report.hr_payroll.contribution_register'
    _description = 'Model for Printing hr.payslip.line grouped by register'

    def _get_report_values(self, docids, data):
        docs = []
        lines_data = {}
        lines_total = {}

        for result in self.env['hr.payslip.line'].read_group([('id', 'in', docids)], ['partner_id', 'total', 'ids:array_agg(id)'], ['partner_id']):
            if result['partner_id']:
                docid = result['partner_id'][0]
                docs.append(docid)
                lines_data[docid] = self.env['hr.payslip.line'].browse(result['ids'])
                lines_total[docid] = result['total']

        return {
            'docs': self.env['res.partner'].browse(docs),
            'data': data,
            'lines_data': lines_data,
            'lines_total': lines_total
        }
