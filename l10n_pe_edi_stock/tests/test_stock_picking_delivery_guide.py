# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.l10n_pe_edi.tests.common import TestPeEdiCommon
from odoo.tests import tagged

class TestPEDeliveryGuideCommon(TestPeEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_wh = cls.env['stock.warehouse'].create({
            'name': 'New Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'NWH'
        })

        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.productA = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_01010101').id,
            'weight': 1,
            'barcode': '123456789',
        })

        cls.certificate.write({
            'date_start': datetime.today() - relativedelta(years=1),
            'date_end': datetime.today() + relativedelta(years=1),
        })

        cls.company_data['company'].partner_id.l10n_latam_identification_type_id = cls.env.ref('l10n_pe.it_RUC')
        cls.company_data['company'].partner_id.l10n_pe_district = cls.env.ref('l10n_pe.district_pe_030101')
        cls.company_data['company'].partner_id.street = 'Rocafort 314'

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Partner A',
            'street_number': '728',
            'street_name': 'Street Calle',
            'city': 'Arteaga',
            'country_id': cls.env.ref('base.pe').id,
            'state_id': cls.env.ref('base.state_pe_15').id,
            'l10n_pe_district': cls.env.ref('l10n_pe.district_pe_030101').id,
            'zip': '25350',
            'vat': '20100105862',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_pe.it_RUC').id,
        })

        cls.operator_luigys = cls.env.ref('l10n_pe_edi_stock.partner_pe_transporte_operador')

        cls.vehicle_luigys = cls.env['l10n_pe_edi.vehicle'].create({
            'name': 'PE TRUCK',
            'license_plate': 'ABC123',
            'operator_id':  cls.operator_luigys.id,
        })

        cls.picking = cls.env['stock.picking'].create({
            'location_id': cls.new_wh.lot_stock_id.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.new_wh.out_type_id.id,
            'partner_id': cls.partner_a.id,
            'l10n_pe_edi_transport_type': '01',
            'l10n_pe_edi_vehicle_id': cls.vehicle_luigys.id,
            'l10n_pe_edi_operator_id': cls.operator_luigys.id,
            'l10n_pe_edi_reason_for_transfer': '01',
            'l10n_pe_edi_departure_start_date': datetime.today(),
        })

        cls.env['stock.move'].create({
            'name': cls.productA.name,
            'product_id': cls.productA.id,
            'product_uom_qty': 10,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking.id,
            'location_id': cls.new_wh.lot_stock_id.id,
            'location_dest_id': cls.customer_location.id,
            'state': 'confirmed',
            'description_picking': cls.productA.name,
        })
        cls.env['stock.quant']._update_available_quantity(cls.productA, cls.new_wh.lot_stock_id, 10.0)
        cls.picking.action_assign()
        cls.picking.move_ids[0].move_line_ids[0].qty_done = 10
        cls.picking._action_done()


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestGeneratePEDeliveryGuide(TestPEDeliveryGuideCommon):
    def test_generate_delivery_guide(self):
        """ Check the XML in the test delivery is correctly generated """
        ubl = self.picking._l10n_pe_edi_create_delivery_guide()
        expected_document = '''
<DespatchAdvice
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns="urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2"
    xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
    <ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionContent>
                <ds:Signature Id="placeholder">
                </ds:Signature>
            </ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>
    <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>1.0</cbc:CustomizationID>
    <cbc:ID>___ignore___</cbc:ID>
    <cbc:IssueDate>___ignore___</cbc:IssueDate>
    <cbc:IssueTime>___ignore___</cbc:IssueTime>
    <cbc:DespatchAdviceTypeCode>09</cbc:DespatchAdviceTypeCode>
    <cbc:Note>Guía</cbc:Note>
    <cac:DespatchSupplierParty>
        <cbc:CustomerAssignedAccountID schemeID="6">20557912879</cbc:CustomerAssignedAccountID>
        <cac:Party>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>company_1_data</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:DespatchSupplierParty>
    <cac:DeliveryCustomerParty>
        <cbc:CustomerAssignedAccountID schemeID="6">20100105862</cbc:CustomerAssignedAccountID>
        <cac:Party>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>Partner A</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:DeliveryCustomerParty>
    <cac:Shipment>
        <cbc:ID>1</cbc:ID>
        <cbc:HandlingCode>01</cbc:HandlingCode>
        <cbc:Information>Sale</cbc:Information>
        <cbc:GrossWeightMeasure unitCode="KGM">10.000</cbc:GrossWeightMeasure>
        <cbc:SplitConsignmentIndicator>false</cbc:SplitConsignmentIndicator>
        <cac:ShipmentStage>
            <cbc:TransportModeCode>01</cbc:TransportModeCode>
            <cac:TransitPeriod><cbc:StartDate>___ignore___</cbc:StartDate></cac:TransitPeriod>
            <cac:TransportMeans>
                <cac:RoadTransport>
                    <cbc:LicensePlateID>ABC123</cbc:LicensePlateID>
                </cac:RoadTransport>
            </cac:TransportMeans>
            <cac:DriverPerson>
                <cbc:ID schemeID="6">20100030595</cbc:ID>
            </cac:DriverPerson>
        </cac:ShipmentStage>
        <cac:Delivery>
            <cac:DeliveryAddress>
                <cbc:ID>030101</cbc:ID>
                <cbc:StreetName>Street Calle 728</cbc:StreetName>
            </cac:DeliveryAddress>
        </cac:Delivery>
        <cac:TransportHandlingUnit>
            <cbc:ID>ABC123</cbc:ID>
            <cac:TransportEquipment>
                <cbc:ID>ABC123</cbc:ID>
            </cac:TransportEquipment>
        </cac:TransportHandlingUnit>
        <cac:OriginAddress>
            <cbc:ID>030101</cbc:ID>
            <cbc:StreetName>Rocafort 314</cbc:StreetName>
        </cac:OriginAddress>
        </cac:Shipment>
        <cac:DespatchLine>
            <cbc:ID>1</cbc:ID>
            <cbc:DeliveredQuantity unitCode="NIU">10.0000000000</cbc:DeliveredQuantity>
            <cac:OrderLineReference>
                <cbc:LineID>1</cbc:LineID>
            </cac:OrderLineReference>
            <cac:Item>
                <cbc:Name>Product A</cbc:Name>
                <cac:SellersItemIdentification>
                    <cbc:ID>123456789</cbc:ID>
                </cac:SellersItemIdentification>
            </cac:Item>
        </cac:DespatchLine>
    </DespatchAdvice>
        '''
        current_etree = self.get_xml_tree_from_string(ubl)
        expected_etree = self.get_xml_tree_from_string(expected_document)
        self.assertXmlTreeEqual(current_etree, expected_etree)


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestSendPEDeliveryGuide(TestPEDeliveryGuideCommon):
    def test_send_delivery_guide(self):
        """Ensure that delivery guide is generated and signed in the SUNAT."""
        self.picking.l10n_latam_document_number = 'T001-%s' % datetime.now().strftime('%H%M%S')
        self.picking.action_send_delivery_guide()
        self.assertEqual(self.picking.l10n_pe_edi_status, 'sent', self.picking.l10n_pe_edi_error)
