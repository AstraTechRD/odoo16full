# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

@tagged('-at_install', 'post_install')
class TestUi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_thibault = cls.env['hr.employee'].create({
            'name': 'Thibault',
            'work_email': 'thibault@a.be',
            'tz': 'UTC',
            'employee_type': 'freelance',
            'flexible_hours': True,
        })

    def test_01_ui(self):
        self.start_tour("/", 'planning_test_tour', login='admin')
