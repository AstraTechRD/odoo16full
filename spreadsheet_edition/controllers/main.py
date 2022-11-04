import logging
import zipfile
import json
import io

from odoo import http
from odoo.http import request, content_disposition, Controller

logger = logging.getLogger(__name__)


class SpreadsheetController(Controller):

    def _generate_xlsx_content(self, files):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as doc_zip:
            for f in files:
                doc_zip.writestr(f['path'], f['content'])

        return stream.getvalue()

    @http.route('/spreadsheet/xlsx', type='http', auth="user", methods=["POST"])
    def get_xlsx_file(self, zip_name, files, **kw):
        files = json.loads(files)

        content = self._generate_xlsx_content(files)
        headers = [
            ('Content-Length', len(content)),
            ('Content-Type', 'application/vnd.ms-excel'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Disposition', content_disposition(zip_name))
        ]

        response = request.make_response(content, headers)
        return response
