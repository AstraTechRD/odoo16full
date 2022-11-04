# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests import tagged
from odoo.tests.common import can_import
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

@tagged("post_install", "-at_install")
class TestXLSXImport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        coa_file = "account_base_import/static/src/xls/coa_import.xlsx"
        journal_items_file = "account_base_import/static/src/xls/journal_items_import.xlsx"
        with file_open(coa_file, "rb") as f:
            cls.coa_file_content = f.read()
        with file_open(journal_items_file, "rb") as f:
            cls.journal_items_file_content = f.read()

    @unittest.skipUnless(can_import("xlrd.xlsx"), "XLRD module not available")
    def test_account_xlsx_import(self):
        existing_id = self.env["account.account"].with_context(import_file=True).create({"code":"550003", "name": "Existing Account"}).id

        import_wizard = self.env["base_import.import"].create({
            "res_model": "account.account",
            "file": self.coa_file_content,
            "file_type": "application/vnd.ms-excel"
        })
        preview = import_wizard.parse_preview({
            "has_headers": True,
        })

        result = import_wizard.execute_import(
            preview["headers"],
            preview["headers"],
            preview["options"]
        )

        self.assertEqual(result["messages"], [], "The import should have been successful without error")

        existing_account = self.env["account.account"].browse(existing_id)
        self.assertEqual(len(result["ids"]), 14, "14 Accounts should have been imported")
        self.assertEqual(existing_account.name, "Bank", "The existing account should have been updated")
        self.assertEqual(existing_account.current_balance, -3500.0, "The balance should have been updated")

    @unittest.skipUnless(can_import("xlrd.xlsx"), "XLRD module not available")
    def test_account_move_line_xlsx_import(self):
        import_wizard = self.env["base_import.import"].with_company(self.env.company).create({
            "res_model": "account.move.line",
            "file": self.journal_items_file_content,
            "file_type": "application/vnd.ms-excel"
        })

        preview = import_wizard.parse_preview({
            "has_headers": True,
        })
        preview["options"]["name_create_enabled_fields"] = {
            "journal_id": True,
            "account_id": True,
            "partner_id": True,
        }

        result = import_wizard.with_company(self.env.company).execute_import(
            preview["headers"],
            preview["headers"],
            preview["options"]
        )

        account_move_lines = self.env["account.move.line"].browse(result["ids"])
        self.assertEqual(len(account_move_lines.mapped("move_id").ids), 2, "2 moves should have been created")
        self.assertEqual(account_move_lines.mapped("journal_id.code"), ["MISC", "SAL"], "The journals should be set correctly")
        self.assertEqual(account_move_lines.mapped("account_id.code"), ["700200", "400000", "455000", "620200"], "The accounts should be set correctly")
