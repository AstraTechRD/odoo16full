# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

@tagged('-at_install', 'post_install')
class TestUi(HttpCase):
    def test_01_ui(self):
        self.start_tour("/", 'project_enterprise_tour', login='admin')
