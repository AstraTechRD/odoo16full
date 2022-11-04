# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.l10n_mx_edi_40.tests.common import TestMxEdiCommon

class TestMXDeliveryGuideCommon(TestMxEdiCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Adjust Demo Data since the PAC's only sign documents with valid companies
        cls.env['res.company'].search([('name', '=', 'ESCUELA KEMPER URGATE')]).name = 'The school formally known as KEMPER URGATE'

        cls.company_values = {
            'name': 'ESCUELA KEMPER URGATE',
            'zip': '20928',
            'state_id': cls.env.ref('base.state_mx_ags').id,
            'l10n_mx_edi_pac': 'finkok',
        }
        cls.company_data['company'].write(cls.company_values)

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
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_56101500').id,
            'weight': 1,
        })

        cls.certificate.write({
            'date_start': datetime.today() - relativedelta(years=1),
            'date_end': datetime.today() + relativedelta(years=1),
        })

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'INMOBILIARIA',
            'street': 'Street Calle',
            'city': 'Hidalgo del Parral',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_chih').id,
            'zip': '33826',
            'vat': 'ICV060329BY0',
        })

        cls.operator_pedro = cls.env['res.partner'].create({
            'name': 'Amigo Pedro',
            'vat': 'VAAM130719H60',
            'street': 'JESUS VALDES SANCHEZ',
            'city': 'Arteaga',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_coah').id,
            'zip': '25350',
            'l10n_mx_edi_operator_licence': 'a234567890',
        })

        cls.figure_1 = cls.env['l10n_mx_edi.figure'].create({
            'type': '01',
            'operator_id': cls.operator_pedro.id,
        })

        cls.figure_2 = cls.env['l10n_mx_edi.figure'].create({
            'type': '02',
            'operator_id': cls.env.company.partner_id.id,
            'part_ids': [(4, cls.env.ref('l10n_mx_edi_stock.l10n_mx_edi_part_05').id)],
        })

        cls.vehicle_pedro = cls.env['l10n_mx_edi.vehicle'].create({
            'name': 'DEMOPERMIT',
            'transport_insurer': 'DEMO INSURER',
            'transport_insurance_policy': 'DEMO POLICY',
            'transport_perm_sct': 'TPAF10',
            'vehicle_model': '2020',
            'vehicle_config': 'T3S1',
            'vehicle_licence': 'ABC123',
            'trailer_ids': [(0, 0, {'name': 'trail1', 'sub_type': 'CTR003'})],
            'figure_ids': [(4, cls.figure_1.id, 0), (4, cls.figure_2.id, 0)],
        })

        cls.picking = cls.env['stock.picking'].create({
            'location_id': cls.new_wh.lot_stock_id.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.new_wh.out_type_id.id,
            'partner_id': cls.partner_a.id,
            'l10n_mx_edi_transport_type': '01',
            'l10n_mx_edi_vehicle_id': cls.vehicle_pedro.id,
            'l10n_mx_edi_distance': 120,
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
