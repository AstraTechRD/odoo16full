# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.base_iban.models.res_partner_bank import validate_iban


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _get_invalid_iban_employee_ids(self):
        # as acc_type isn't stored we can not use a domain to retrieve the employees
        # bypass orm for performance, we only care about the employee id anyway

        # return nothing if user has no right to either employee or bank partner
        try:
            self.check_access_rights('read')
            self.env['res.partner.bank'].check_access_rights('read')
        except AccessError:
            return []

        self.env.cr.execute('''
            SELECT emp.id,
                   acc.acc_number
              FROM hr_employee emp
         LEFT JOIN res_partner_bank acc
                ON acc.id=emp.bank_account_id
              JOIN hr_contract con
                ON con.employee_id=emp.id
             WHERE emp.company_id IN %s
               AND emp.active=TRUE
               AND con.state='open'
        ''', (tuple(self.env.companies.ids),))

        def valid_iban(iban):
            if iban is None:
                return False
            try:
                validate_iban(iban)
                return True
            except ValidationError:
                pass
            return False
        return [row['id'] for row in self.env.cr.dictfetchall() if not valid_iban(row['acc_number'])]
