# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning

from .sendcloud_service import SendCloud


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[
        ('sendcloud', 'Sendcloud')
    ], ondelete={'sendcloud': lambda records: records.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    sendcloud_public_key = fields.Char(help="Sendcloud API Integration Public key")
    sendcloud_secret_key = fields.Char(help="Sendcloud API Integration Secret key")
    sendcloud_default_package_type_id = fields.Many2one("stock.package.type", string="Default Package Type for Sendcloud", help="Some carriers require package dimensions, you can define these in a package type that you set as default")
    sendcloud_shipping_id = fields.Many2one('sendcloud.shipping.product', string="Sendcloud Shipping Product")
    sendcloud_return_id = fields.Many2one('sendcloud.shipping.product', string="Sendcloud Return Shipping Product")
    sendcloud_shipping_rules = fields.Selection([('ship', 'Shipping'), ('return', 'Returns'), ('both', 'Both')], string="Use Sendcloud shipping rules",
                                                help="Depending your Sendcloud account type, through rules you can define the shipping method to use depending on different conditions like destination, weight, value, etc. \n \
                                                    Rules can override shipping product selected in odoo")

    @api.constrains('delivery_type', 'sendcloud_public_key', 'sendcloud_secret_key')
    def _check_sendcloud_api_keys(self):
        for rec in self:
            if rec.delivery_type == 'sendcloud' and not (rec.sendcloud_public_key and rec.sendcloud_secret_key):
                raise ValidationError(_('You must add your public and secret key for sendcloud delivery type!'))

    def _compute_can_generate_return(self):
        super()._compute_can_generate_return()
        self.filtered(lambda c: c.delivery_type == 'sendcloud').write({'can_generate_return': True})

    def action_load_sendcloud_shipping_products(self):
        """
        Returns a wizard to choose from available sendcloud shipping products.
        Since the shipping product ids in sendcloud change overtime they are not saved,
        instead they are fetched everytime and passed to the context of the wizard
        """
        self.ensure_one()
        if self.delivery_type != 'sendcloud':
            raise ValidationError(_('Must be a Sendcloud carrier!'))
        sendcloud = SendCloud(self.sendcloud_public_key, self.sendcloud_secret_key, self.log_xml)
        # Get normal and return shipping products (can't get both at once)
        shipping_products = sendcloud.get_shipping_products()
        return_products = sendcloud.get_shipping_products(is_return=True)
        if not shipping_products:
            raise UserError('There are no shipping products available, please activate carriers in your account')
        return {
            'name': _("Choose Sendcloud Shipping Products"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sendcloud.shipping.wizard',
            'target': 'new',
            'context': {
                'shipping_products': shipping_products,
                'return_products': return_products,
                'return_on_delivery': self.return_label_on_delivery,
                'default_carrier_id': self.id
            },
        }

    def sendcloud_rate_shipment(self, order):
        """ Returns shipping rate for the order and chosen shipping method """
        sendcloud = SendCloud(self.sendcloud_public_key, self.sendcloud_secret_key, self.log_xml)
        price, packages_no = sendcloud.get_shipping_rate(self, order=order)
        message = None
        if packages_no:
            message = _('Note that this price is for %s packages since the order weight is more than max weight of the shipping method.', packages_no)
        return {
            'success': True,
            'price': price,
            'warning_message': message
        }

    def sendcloud_send_shipping(self, pickings):
        ''' Sends Shipment to sendcloud, must request rate to return exact price '''
        sendcloud = SendCloud(self.sendcloud_public_key, self.sendcloud_secret_key, self.log_xml)
        res = []
        for pick in pickings:
            # multiple parcels if several packages used
            parcels = sendcloud.send_shipment(pick)
            # fetch the ids, tracking numbers and url for each parcel
            parcel_ids, parcel_tracking_numbers, doc_ids = self._prepare_track_message_docs(pick, parcels, sendcloud)
            pick.message_post_with_view(
                'delivery_sendcloud.sendcloud_label_tracking', values={'type': 'Shipment', 'parcels': parcels},
                subtype_id=self.env.ref('mail.mt_note').id, author_id=self.env.user.partner_id.id, attachment_ids=doc_ids
            )
            # pick.message_post(body=logmessage, attachments=docs)
            parcel_ids = ','.join(parcel_ids)
            pick.sendcloud_parcel_ref = parcel_ids
            try:
                # generate return if config is set
                if pick.carrier_id.return_label_on_delivery:
                    self.get_return_label(pick)
            except UserError:
                # if the return fails need to log that they failed and continue
                pick.message_post(body=_('Failed to create the return label!'))

            try:
                # get exact price of shipment
                price = 0.0
                for parcel in parcels:
                    # get price for each parcel
                    price += sendcloud.get_shipping_rate(pick.carrier_id, picking=pick, parcel=parcel)[0]
            except UserError:
                # if the price fetch fails need to log that they failed and continue
                pick.message_post(body=_('Failed to get the actual price!'))

            # get tracking numbers for parcels
            parcel_tracking_numbers = ','.join(parcel_tracking_numbers)
            # if in test env, sendcloud does not have one, so we cancel the shipment ASAP
            if not self.prod_environment:
                self.cancel_shipment(pick)
                msg = _("Shipment %s cancelled", parcel_tracking_numbers)
                pick.message_post(body=msg)
                parcel_tracking_numbers = None
            res.append({
                'exact_price': price,
                'tracking_number': parcel_tracking_numbers
            })
        return res

    def sendcloud_get_tracking_link(self, picking):
        sendcloud = SendCloud(self.sendcloud_public_key, self.sendcloud_secret_key, self.log_xml)
        # since there can be more than one id stored, comma seperated, only the first will be tracked
        parcel_id = picking.sendcloud_parcel_ref.split(',')[0]
        res = sendcloud.track_shipment(parcel_id)
        return res['tracking_url']

    def sendcloud_get_return_label(self, picking, tracking_number=None, origin_date=None):
        sendcloud = SendCloud(self.sendcloud_public_key, self.sendcloud_secret_key, self.log_xml)
        parcels = sendcloud.send_shipment(picking=picking, is_return=True)
        # fetch the ids, tracking numbers and url for each parcel
        parcel_ids, _, doc_ids = self._prepare_track_message_docs(picking, parcels, sendcloud)
        parcel_ids = ','.join(parcel_ids)
        # Add Tracking info and docs in chatter
        picking.message_post_with_view(
            'delivery_sendcloud.sendcloud_label_tracking', values={'type': 'Return', 'parcels': parcels},
            subtype_id=self.env.ref('mail.mt_note').id, author_id=self.env.user.partner_id.id, attachment_ids=doc_ids
        )
        # if picking is not a return means we are pregenerating the return label on delivery
        # thus we save the returned parcel id in a seperate field
        if picking.is_return_picking:
            picking.sendcloud_parcel_ref = parcel_ids
        else:
            picking.sendcloud_return_parcel_ref = parcel_ids

    def sendcloud_cancel_shipment(self, pickings):
        sendcloud = SendCloud(self.sendcloud_public_key, self.sendcloud_secret_key, self.log_xml)
        for pick in pickings:
            for parcel_id in pick.sendcloud_parcel_ref.split(','):
                res = sendcloud.cancel_shipment(parcel_id)
                if res.get('status') not in ['deleted', 'cancelled', 'queued']:
                    raise UserError(res.get('message'))
            if pick.sendcloud_return_parcel_ref:
                for ret_parcel_id in pick.sendcloud_return_parcel_ref.split(','):
                    sendcloud.cancel_shipment(ret_parcel_id)

    def sendcloud_convert_weight(self, weight, grams=False):
        """
            Each API request for sendcloud usually requires
            weight in kilograms but pricing supports grams.
        """
        if weight == 0:
            return weight
        weight_uom_id = self.env['product.template'].sudo()._get_weight_uom_id_from_ir_config_parameter()
        if grams:
            converted_weight = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_gram'))
        else:
            converted_weight = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'))
        return converted_weight

    def raise_redirect_message(self):
        self.ensure_one()
        raise RedirectWarning(
            _('You must have a shipping product configured!'),
            {
                'type': 'ir.actions.act_window',
                'name': self.name,
                'res_model': 'delivery.carrier',
                'view_mode': 'form',
                'res_id': self.id,
            },
            _("Go to the shipping method"),
        )

    def _prepare_track_message_docs(self, picking, parcels, sendcloud):
        docs = []
        parcel_ids = []
        parcel_tracking_numbers = []
        for parcel in parcels:
            if not parcel.get('tracking_number', ''):
                raise ValidationError(_('Label not received by carrier, please try again later'))
            parcel_ids.append(str(parcel['id']))
            parcel_tracking_numbers.append(parcel['tracking_number'])
            # this will include documents to print such as label
            # https://api.sendcloud.dev/docs/sendcloud-public-api/parcel-documents/operations/get-a-parcel-document
            # sendcloud docs mention there are 7 doc types
            # so we limit the loop to 7 docs
            for doc in parcel['documents'][:7]:
                doc_content = sendcloud.get_document(doc['link'])
                doc_type = doc['type'].capitalize()
                doc_title = f"Sendcloud {doc_type}-{parcel['id']}.pdf"
                docs.append({
                    'name': doc_title,
                    'type': 'binary',
                    'raw': doc_content,
                    'res_model': picking._name,
                    'res_id': picking.id
                })
        doc_ids = self.env['ir.attachment'].create(docs)

        return parcel_ids, parcel_tracking_numbers, doc_ids
