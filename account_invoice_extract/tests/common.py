# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.account_invoice_extract.models.account_invoice import AccountMove
from odoo.addons.base.models.ir_cron import ir_cron
from odoo.addons.iap.models.iap_account import IapAccount
from odoo.addons.partner_autocomplete.models.iap_autocomplete_api import IapAutocompleteEnrichAPI
from odoo.sql_db import Cursor
from odoo.tests import common


class MockIAP(common.BaseCase):
    @contextmanager
    def mock_iap_extract(self, extract_response, partner_autocomplete_response):
        def _trigger(self, *args, **kwargs):
            # A call to _trigger will directly run the cron
            self.method_direct_trigger()

        # The module iap is committing the transaction when creating an IAP account, we mock it to avoid that
        with patch.object(AccountMove, '_contact_iap_extract', side_effect=lambda *args, **kwargs: extract_response), \
                patch.object(IapAutocompleteEnrichAPI, '_contact_iap', side_effect=lambda *args, **kwargs: partner_autocomplete_response), \
                patch.object(IapAccount, 'get_credits', side_effect=lambda *args, **kwargs: 1), \
                patch.object(Cursor, 'commit', side_effect=lambda *args, **kwargs: None), \
                patch.object(ir_cron, '_trigger', side_effect=_trigger, autospec=True):
            yield
