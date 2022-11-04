# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import SpreadsheetTestCommon
from odoo.tools import file_open
from odoo.exceptions import UserError

class SpreadsheetImportXlsx(SpreadsheetTestCommon):
    def test_import_xlsx(self):
        """Import xlsx"""
        folder = self.env["documents.folder"].create({"name": "Test folder"})
        with file_open('documents_spreadsheet/tests/data/test.xlsx', 'rb') as f:
            raw = f.read()
            document_xlsx = self.env['documents.document'].create({
                'raw': raw,
                'name': 'text.xlsx',
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'folder_id': folder.id
            })
            spreadsheet_id = document_xlsx.clone_xlsx_into_spreadsheet()
            spreadsheet = self.env["documents.document"].browse(spreadsheet_id).exists()
            self.assertTrue(spreadsheet)

    def test_import_xlsx_wrong_mime_type(self):
        """Import xlsx with wrong mime type raisese an error"""
        folder = self.env["documents.folder"].create({"name": "Test folder"})
        with file_open('documents_spreadsheet/tests/data/test.xlsx', 'rb') as f:
            raw = f.read()
            document_xlsx = self.env['documents.document'].create({
                'raw': raw,
                'name': 'text.xlsx',
                'mimetype': 'text/plain',
                'folder_id': folder.id
            })
            with self.assertRaises(UserError) as error_catcher:
                document_xlsx.clone_xlsx_into_spreadsheet()

            self.assertEqual(error_catcher.exception.args[0], ("The file is not a xlsx file"))


    def test_import_xlsx_wrong_content(self):
        """Import a xlsx which isn't a zip raises error"""
        folder = self.env["documents.folder"].create({"name": "Test folder"})
        document_xlsx = self.env['documents.document'].create({
            'raw': b"yolo",
            'name': 'text.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'folder_id': folder.id
        })
        with self.assertRaises(UserError) as error_catcher:
            document_xlsx.clone_xlsx_into_spreadsheet()

        self.assertEqual(error_catcher.exception.args[0], ("The file is not a xlsx file"))

    def test_import_xlsx_zip_but_not_xlsx(self):
        """Import a zip which isn't a xlsx raises error"""
        folder = self.env["documents.folder"].create({"name": "Test folder"})
        document_xlsx = self.env['documents.document'].create({
            # Minimum zip file
            'raw': b"\x50\x4B\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            'name': 'text.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'folder_id': folder.id
        })
        with self.assertRaises(UserError) as error_catcher:
            document_xlsx.clone_xlsx_into_spreadsheet()

        self.assertEqual(error_catcher.exception.args[0], ("The xlsx file is corrupted"))
