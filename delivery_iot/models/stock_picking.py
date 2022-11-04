# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    iot_scale_ids = fields.Many2many(
        'iot.device',
        string="Scales",
        domain=[('type', '=', 'scale')],
        help="Choose the scales you want to use for this operation type. Those scales can be used to weigh the packages created."
    )
    iot_printer_id = fields.Many2one(
        'iot.device',
        string='Shipping Labels Printer',
        domain=[('type', '=', 'printer')],
        help="Automatically print the shipping labels using this printer."
    )

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        message = super(StockPicking, self).message_post(**kwargs)
        if message.attachment_ids and 'Label' in ''.join(message.attachment_ids.mapped('name')) and self.picking_type_id.iot_printer_id:
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'iot_print_documents', {
                'documents': message.attachment_ids.mapped('datas'),
                'iot_device_identifier': self.picking_type_id.iot_printer_id.identifier,
                'iot_ip': self.picking_type_id.iot_printer_id.iot_ip,
            })
        return message
