odoo.define('pos_l10n_se.OrderReceipt', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');

    const PosSwedenOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            get receiptEnv () {
                if (this.env.pos.useBlackBoxSweden()) {
                    let receipt_render_env = super.receiptEnv;
                    receipt_render_env.receipt.useBlackBoxSweden = true;
                    receipt_render_env.receipt.company.street = this.env.pos.company.street;
                    receipt_render_env.receipt.posID = this.env.pos.config.id;

                    receipt_render_env.receipt.orderSequence = receipt_render_env.order.sequence_number;
                    receipt_render_env.receipt.unitID = receipt_render_env.order.blackbox_unit_id;
                    receipt_render_env.receipt.blackboxSignature = receipt_render_env.order.blackbox_signature;

                    receipt_render_env.receipt.originalOrderDate = moment(receipt_render_env.order.creation_date).format("HH:mm DD/MM/YYYY");

                    return receipt_render_env;
                }
                return super.receiptEnv;
            }
            getProductlines(){
                return _.filter(this.receiptEnv.receipt.orderlines, function (orderline) {
                    return orderline.product_type !== "service";
                });
            }
            getServicelines(){
                return _.filter(this.receiptEnv.receipt.orderlines, function (orderline) {
                    return orderline.product_type === "service";
                });
            }

        };

    Registries.Component.extend(OrderReceipt, PosSwedenOrderReceipt);

    return PosSwedenOrderReceipt;
});
