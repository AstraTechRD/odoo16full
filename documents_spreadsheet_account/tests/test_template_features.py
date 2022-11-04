import base64

from odoo.tests import tagged
from odoo.tests.common import HttpCase

TEXT = base64.b64encode(bytes('{"sheets": [{"cells":{"A1":{"content":"😃"}}}]}', 'utf-8'))

@tagged('post_install', '-at_install')
class TestSpreadsheetTemplateFeatures(HttpCase):

    def test_spreadsheet_templates_features(self):
        self.env["spreadsheet.template"].create({
            "data": TEXT,
            "name": "Template with special characters",
        })
        self.start_tour('/web', 'spreadsheet_template_features', login='admin')
