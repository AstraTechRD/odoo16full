# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime

from odoo import fields, models, _
from odoo.modules import get_module_resource


class ExpenseSampleReceipt(models.Model):
    _name = 'expense.sample.receipt'
    _description = 'Try Sample Receipts'

    def _action_create_expense(self, values, sample_number):
        fallback_employee = self.env['hr.employee'].search([], limit=1) or self.env['hr.employee'].create({
            'name': _('Sample Employee'),
            'company_id': self.env.company.id,
        })
        product = self.env.ref('hr_expense.product_product_no_cost')

        # 3/ Compute the line values
        expense_line_values = {
            'name': _("Sample Receipt: %s", values['name']),
            'product_id': product.id,
            'unit_amount': values['amount'],
            'quantity': 1.0,
            'date': values['date'],
            'tax_ids': [(5, 0, 0)],
            'sample': True,
            'employee_id': self.env.user.employee_id.id or fallback_employee.id,
        }

        # 4/ Ensure we have a jounal
        if not self.env['hr.expense.sheet']._default_journal_id():
            self.env['account.journal'].create({
                'type': 'purchase',
                'company_id': self.env.company.id,
                'name': 'Sample Journal',
                'code': 'SAMPLE_P',
            }).id

        # 5/ Create the expense
        expense = self.env['hr.expense'].create(expense_line_values)

        # 6/ Link the attachment
        image_path = get_module_resource('hr_expense_extract', 'static/img', 'sample_%s.jpeg' % sample_number)
        image = base64.b64encode(open(image_path, 'rb').read())
        self.env['ir.attachment'].create({
            'name': 'sample_receipt.jpeg',
            'res_id': expense.id,
            'res_model': 'hr.expense',
            'datas': image,
            'type': 'binary',
        })

        return {
            'name': expense.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'form',
            'res_id': expense.id,
        }

    def action_choose_sample_1(self):
        return self._action_create_expense({
            'name': 'External training',
            'amount': 1995.6,
            'date': datetime.date(2020, 6, 29)
        }, 1)

    def action_choose_sample_2(self):
        return self._action_create_expense({
            'name': 'Restaurant',
            'amount': 17.02,
            'date': datetime.date(2020, 6, 29)
        }, 2)

    def action_choose_sample_3(self):
        return self._action_create_expense({
            'name': 'Office Furniture',
            'amount': 5040.65,
            'date': datetime.date(2020, 6, 29)
        }, 3)

    def action_choose_sample_4(self):
        return self._action_create_expense({
            'name': 'Travel',
            'amount': 700,
            'date': datetime.date(2020, 6, 29)
        }, 4)
