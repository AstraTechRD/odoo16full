odoo.define('pos_blackbox_be.OrderReceipt', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');

    const PosBlackBoxBeOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            get receiptEnv () {
                if (this.env.pos.useBlackBoxBe()) {
                    let receipt_render_env = super.receiptEnv;
                    let order = this.env.pos.get_order();
                    receipt_render_env.receipt.company.street = this.env.pos.company.street;

                    receipt_render_env.receipt.blackboxSignature = order.blackbox_signature;
                    receipt_render_env.receipt.terminalId = order.blackbox_terminal_id;
                    receipt_render_env.receipt.blackboxHashChain = order.blackbox_hash_chain;
                    receipt_render_env.receipt.posProductionId = order.blackbox_pos_production_id;
                    receipt_render_env.receipt.versionId = order.blackbox_pos_production_id;
                    receipt_render_env.receipt.pluHash = order.blackbox_plu_hash;
                    receipt_render_env.receipt.vscIdentificationNumber = order.blackbox_vsc_identification_number;
                    receipt_render_env.receipt.blackboxFdmNumber = order.blackbox_unique_fdm_production_number;
                    receipt_render_env.receipt.ticketCounter = order.blackbox_ticket_counters;
                    receipt_render_env.receipt.blackboxTime = order.blackbox_time;
                    receipt_render_env.receipt.blackboxDate = order.blackbox_date;

                    return receipt_render_env;
                }
            }
        };

    Registries.Component.extend(OrderReceipt, PosBlackBoxBeOrderReceipt);

    return OrderReceipt;
});
