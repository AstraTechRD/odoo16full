# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _get_work_duration(self, date_start, date_stop):
        """
        Returns the amount of hours worked from date_start to date_stop related to the work entry.

        This method is meant to be overriden, see hr_work_entry_contract_attendance
        """
        dt = date_stop - date_start
        return dt.days * 24 + dt.seconds / 3600
