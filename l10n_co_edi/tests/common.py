# coding: utf-8
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged
from odoo.tools import misc

from unittest.mock import patch, Mock
from freezegun import freeze_time
import datetime
from contextlib import contextmanager

from pytz import timezone


class TestCoEdiCommon(AccountEdiTestCommon):

    @contextmanager
    def mock_carvajal(self):
        return_value_upload = {
            'message': 'mocked success',
            'transactionId': 'mocked_success',
        }

        return_value_check = {
            'filename': 'mock_signed_file',
            'xml_file': b'file_content',
            'attachments': None,
            'l10n_co_edi_cufe_cude_ref': 'cufe_cude ref',
            'message': 'successfully mocked'
        }

        try:
            with freeze_time(self.frozen_today), \
                 patch('odoo.addons.l10n_co_edi.models.carvajal_request.CarvajalRequest.upload',
                       new=Mock(return_value=return_value_upload)), \
                 patch('odoo.addons.l10n_co_edi.models.carvajal_request.CarvajalRequest.check_status',
                       new=Mock(return_value=return_value_check)), \
                 patch('odoo.addons.l10n_co_edi.models.carvajal_request.CarvajalRequest.client',
                       new=Mock(return_value=None)):
                yield
        finally:
            pass


    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_co.l10n_co_chart_template_generic',
                   edi_format_ref='l10n_co_edi.edi_carvajal'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_today = datetime.datetime(year=2020, month=8, day=27, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        cls.salesperson = cls.env.ref('base.user_admin')
        cls.salesperson.function = 'Sales'

        report_text = 'GRANDES CONTRIBUYENTES SHD Res. DDI-042065 13-10-17'
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.co').id,
            'l10n_co_edi_header_gran_contribuyente': report_text,
            'l10n_co_edi_header_tipo_de_regimen': report_text,
            'l10n_co_edi_header_retenedores_de_iva': report_text,
            'l10n_co_edi_header_autorretenedores': report_text,
            'l10n_co_edi_header_resolucion_aplicable': report_text,
            'l10n_co_edi_header_actividad_economica': report_text,
            'l10n_co_edi_header_bank_information': report_text,
            'l10n_co_edi_username': 'test',
            'l10n_co_edi_password': 'test',
            'l10n_co_edi_company': 'test',
            'l10n_co_edi_account': 'test',
            'vat': '213123432-1',
            'phone': '+1 555 123 8069',
            'website': 'http://www.example.com',
            'email': 'info@yourcompany.example.com',
            'street': 'Route de Ramilies',
            'zip': '1234',
            'city': 'Bogota',
            'state_id': cls.env.ref('base.state_co_01').id,
        })

        cls.company_data['company'].partner_id.write({
            'l10n_latam_identification_type_id': cls.env.ref('l10n_co.rut').id,
            'l10n_co_edi_obligation_type_ids': [(6, 0, [cls.env.ref('l10n_co_edi.obligation_type_1').id])],
            'l10n_co_edi_large_taxpayer': True,
        })
        cls.company_data['default_journal_sale'].write({
            'l10n_co_edi_dian_authorization_end_date': cls.frozen_today,
            'l10n_co_edi_dian_authorization_number': 42,
            'l10n_co_edi_dian_authorization_date': cls.frozen_today,
        })

        cls.company_data_2['company'].write({
            'country_id': cls.env.ref('base.co').id,
            'phone': '(870)-931-0505',
            'website': 'hhtp://wwww.company_2.com',
            'email': 'company_2@example.com',
            'street': 'Route de Eghezée',
            'zip': '4567',
            'city': 'Medellín',
            'state_id': cls.env.ref('base.state_co_02').id,
            'vat': '213.123.432-1',
        })

        cls.company_data_2['company'].partner_id.write({
            'l10n_latam_identification_type_id': cls.env.ref('l10n_co.rut').id,
            'l10n_co_edi_obligation_type_ids': [(6, 0, [cls.env.ref('l10n_co_edi.obligation_type_1').id])],
            'l10n_co_edi_large_taxpayer': True,
        })

        cls.product_a.default_code = 'P0000'

        cls.tax = cls.company_data['default_tax_sale']
        cls.tax.write({
            'amount': 15,
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id
        })
        cls.retention_tax = cls.tax.copy({
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_9').id
        })

        cls.tax_group = cls.env['account.tax'].create({
            'name': 'tax_group',
            'amount_type': 'group',
            'amount': 0.0,
            'type_tax_use': 'sale',
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_0').id,
            'children_tax_ids': [(6, 0, (cls.tax + cls.retention_tax).ids)],
        })

        uom = cls.env.ref('uom.product_uom_unit')
        uom.l10n_co_edi_ubl = 'S7'
        cls.product_a.uom_id = uom

        cls.invoice = cls.env['account.move'].create({
            'partner_id': cls.company_data_2['company'].partner_id.id,
            'move_type': 'out_invoice',
            'ref': 'reference',

            'invoice_user_id': cls.salesperson.id,
            'name': 'OC 123',
            'invoice_payment_term_id': cls.env.ref('account.account_payment_term_end_following_month').id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 150,
                    'price_unit': 250,
                    'discount': 10,
                    'name': 'Line 1',
                    'tax_ids': [(6, 0, (cls.tax.id, cls.retention_tax.id))],
                }),
            ]
        })

        cls.expected_invoice_xml = misc.file_open('l10n_co_edi/tests/accepted_invoice.xml', 'rb').read()

        cls.expected_credit_note_xml = misc.file_open('l10n_co_edi/tests/accepted_credit_note.xml', 'rb').read()
