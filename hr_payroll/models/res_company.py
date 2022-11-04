# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"

    def _create_dashboard_notes(self):
        dashboard_note_tag = self.env.ref('hr_payroll.payroll_note_tag', raise_if_not_found=False)
        if not dashboard_note_tag:
            return
        payroll_users = self.env.ref('hr_payroll.group_hr_payroll_user').users
        for company in self:
            company_payroll_users = payroll_users.filtered(lambda u: company in u.company_ids)
            if not company_payroll_users:
                continue
            self.env['note.note'].sudo().create({
                'tag_ids': [(4, dashboard_note_tag.id)],
                'company_id': company.id,
                'name': _('Note'),
                'memo': self.env['ir.qweb']._render('hr_payroll.hr_payroll_note_demo_content', {
                    'date_today': fields.Date.today().strftime(self.env['res.lang']._lang_get(self.env.user.lang).date_format)})
            })

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._create_dashboard_notes()
        return companies
