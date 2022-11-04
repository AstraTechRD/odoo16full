# -*- coding: utf-8 -*-

from .common import TestMXDeliveryGuideCommon

from odoo.tests import tagged

@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestSendMXDeliveryGuide(TestMXDeliveryGuideCommon):
    def test_send_delivery_guide(self):
        self.picking.l10n_mx_edi_action_send_delivery_guide()
        self.assertFalse(self.picking.l10n_mx_edi_error)
        self.assertEqual(self.picking.l10n_mx_edi_status, 'sent')

        # Test a portion of the PDF content here since the report is only available once the XML is sent
        delivery_report = self.env['ir.actions.report'].search([('report_name', '=', 'stock.report_deliveryslip')], limit=1)
        pdf_content = self.get_xml_tree_from_string(delivery_report._render_qweb_pdf(self.picking.id)[0])
        expected_table_in_pdf = '''
            <table class="table table-sm mt48" name="stock_move_line_table">
                <thead>
                    <tr>
                        <th name="th_sm_product_unspsc_code"><strong>Code</strong></th>
                        <th name="th_sml_product"><strong>Product</strong></th>
                        <th name="th_sml_quantity" class="text-center"><strong>Quantity</strong></th>
                        <th name="th_sm_uom_unspsc_code"><strong>UOM</strong></th>
                        <th name="th_sm_weight"><strong>Weight</strong></th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>
                            <span>56101500</span>
                        </td>
                        <td>
                            <span>Product A</span>
                        </td>
                        <td class="text-center" name="move_line_aggregated_qty_done">
                            <span data-oe-type="float" data-oe-expression="aggregated_lines[line][\'qty_done\']">10.00</span>
                            <span>Units</span>
                        </td>
                        <td>
                            <span>H87</span>
                        </td>
                        <td>
                            <span data-oe-type="float" data-oe-expression="aggregated_lines[line][\'weight\']">10.00</span>
                            <span>kg</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        '''
        expected_etree = self.get_xml_tree_from_string(expected_table_in_pdf)
        self.assertXmlTreeEqual(pdf_content.xpath('//table')[0], expected_etree)

@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestMXDeliveryGuideXSD(TestMXDeliveryGuideCommon):
    def test_xsd_delivery_guide(self):
        cfdi = self.picking._l10n_mx_edi_create_delivery_guide()
        result = self.picking._l10n_mx_edi_validate_with_xsd(cfdi, raise_error=True)
        self.assertTrue(result)
