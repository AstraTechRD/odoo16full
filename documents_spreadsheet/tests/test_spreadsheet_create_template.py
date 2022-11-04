# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import SpreadsheetTestCommon

from odoo.tests import tagged
from odoo.tests.common import HttpCase

@tagged("post_install", "-at_install")
class TestSpreadsheetCreateTemplate(SpreadsheetTestCommon, HttpCase):

    def test_01_spreadsheet_create_template(self):
        self.start_tour("/web", "documents_spreadsheet_create_template_tour", login="admin")
