odoo.define('pos_l10n_se.PrintBillButton', function(require) {
    'use strict';

    const PrintBillButton = require('pos_restaurant.PrintBillButton');
    const Registries = require('point_of_sale.Registries');

    const PosSwedenPrintBillButton = PrintBillButton => class extends PrintBillButton {
        async onClick() {
            let order = this.env.pos.get_order();
            if (this.env.pos.useBlackBoxSweden()) {
                order.isProfo = true;
                order.receipt_type = "profo";
                let sequence = await this.env.pos.get_profo_order_sequence_number();
                order.sequence_number = sequence;

                 await this.env.pos.push_single_order(order);
                 order.receipt_type = false;
            }
            await super.onClick();
            order.isProfo = false;
        }
    };

     Registries.Component.extend(PrintBillButton, PosSwedenPrintBillButton);

     return PosSwedenPrintBillButton;
 });
