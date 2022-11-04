odoo.define('pos_l10n_se.ReprintReceiptButton', function(require) {
    'use strict';

    const ReprintReceiptButton = require('point_of_sale.ReprintReceiptButton');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');
    var core    = require('web.core');
    var _t      = core._t;

    const PosSwedenReprintReceiptButton = ReprintReceiptButton =>
        class extends ReprintReceiptButton {
            async _onClick() {
                if(this.env.pos.useBlackBoxSweden()) {
                    let order = this.props.order;

                    if(order) {
                        let isReprint = await this.rpc({
                            model: 'pos.order',
                            method: 'is_already_reprint',
                            args: [[this.env.pos.validated_orders_name_server_id_map[order.name]]],
                        });
                        if(isReprint) {
                            await Gui.showPopup('ErrorPopup',{
                                'title': _t("POS error"),
                                'body':  _t("A duplicate has already been printed once."),
                            });
                        } else {
                            order.receipt_type = "kopia";
                            await this.env.pos.push_single_order(order);
                            order.receipt_type = false;
                            order.isReprint = true;
                            await this.rpc({
                                model: 'pos.order',
                                method: 'set_is_reprint',
                                args: [[this.env.pos.validated_orders_name_server_id_map[order.name]]],
                            });
                            super._onClick();
                        }
                    }
                } else {
                    super._onClick();
                }
            }
        };

    Registries.Component.extend(ReprintReceiptButton, PosSwedenReprintReceiptButton);

    return PosSwedenReprintReceiptButton;
});
