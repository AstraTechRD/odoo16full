# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    uan = fields.Char(string='UAN', groups="hr.group_hr_user")
    pan = fields.Char(string='PAN', groups="hr.group_hr_user")
    esic_number = fields.Char(string='ESIC Number', groups="hr.group_hr_user")
