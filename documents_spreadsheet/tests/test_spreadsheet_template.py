# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from .common import SpreadsheetTestCommon


TEXT = base64.b64encode(bytes("TEST", 'utf-8'))

class SpreadsheetTemplate(SpreadsheetTestCommon):

    def test_copy_template_without_name(self):
        template = self.env["spreadsheet.template"].create({
            "data": TEXT,
            "name": "Template name",
        })
        self.assertEqual(
            template.copy().name,
            "Template name (copy)",
            "It should mention the template is a copy"
        )

    def test_copy_template_with_name(self):
        template = self.env["spreadsheet.template"].create({
            "data": TEXT,
            "name": "Template name",
        })
        self.assertEqual(
            template.copy({"name": "New Name"}).name,
            "New Name",
            "It should have assigned the given name"
        )

    def test_allow_write_on_own_template(self):
        template = self.env["spreadsheet.template"].with_user(self.spreadsheet_user)\
            .create({
                "data": TEXT,
                "name": "Template name",
            })
        self.assertFalse(
            template.fetch_template_data()["isReadonly"],
            "Document User should be able to edit his own templates"
        )

    def test_forbid_write_on_others_template(self):
        template = self.env["spreadsheet.template"].create({
            "data": TEXT,
            "name": "Template name",
        })
        self.assertTrue(
            template.with_user(self.spreadsheet_user).fetch_template_data()["isReadonly"],
            "Document User cannot edit other's templates"
        )
