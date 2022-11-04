# coding: utf-8
from odoo.addons.l10n_mx_edi_40.tests.common import TestMxEdiCommon

from odoo.tests import tagged


class TestMxExtendedEdiCommon(TestMxEdiCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_mx.mx_coa', edi_format_ref='l10n_mx_edi.edi_cfdi_3_3'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)
        cls.company_data['company'].write({
            'l10n_mx_edi_locality_id': cls.env.ref('l10n_mx_edi_extended.res_locality_mx_son_04').id,
        })

        cls.product.write({
            'l10n_mx_edi_tariff_fraction_id': cls.env.ref('l10n_mx_edi_extended.tariff_fraction_7212100399').id,
            'l10n_mx_edi_umt_aduana_id': cls.env.ref('uom.product_uom_unit').id,
        })
