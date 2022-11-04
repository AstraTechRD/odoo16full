# -*- coding: utf-8 -*-

import io
import zipfile

from odoo import http
from odoo.tests.common import HttpCase


class TestDocumentsRoutes(HttpCase):
    def setUp(self):
        super().setUp()
        self.folder_a = self.env['documents.folder'].create({
            'name': 'folder A',
        })
        self.document_txt = self.env['documents.document'].create({
            'raw': b'TEST',
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
        })

    def test_documents_content(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/documents/content/%s' % self.document_txt.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'TEST')

    def test_documents_zip(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/document/zip', data={
            'file_ids': [self.document_txt.id],
            'zip_name': 'testZip.zip',
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertEqual(response.status_code, 200)
        with io.BytesIO(response.content) as buffer, zipfile.ZipFile(buffer) as zipfile_obj:
            self.assertEqual(zipfile_obj.read(self.document_txt.name), b'TEST')

    def test_documents_from_web(self):
        self.authenticate('admin', 'admin')
        raw_gif = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
        document_gif = self.env['documents.document'].create({
            'raw': raw_gif,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': self.folder_a.id,
        })
        response = self.url_open('/web/image/%s?model=documents.document' % document_gif.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, raw_gif)
