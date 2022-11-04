odoo.define('pos_iot.chrome', function (require) {
    'use strict';

    const core = require('web.core');
    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

    const _t = core._t;

    const PosIoTChrome = (Chrome) =>
        class extends Chrome {
            get lastTransactionStatusButtonIsShown() {
                return this.env.pos.payment_methods.some(pm => pm.use_payment_terminal === 'worldline');
            }

            __showScreen () {
                if (this.mainScreen.name === 'PaymentScreen' &&
                    this.env.pos.get_order().paymentlines.some(pl => pl.payment_method.use_payment_terminal === 'worldline' && ['waiting', 'waitingCard', 'waitingCancel'].includes(pl.payment_status))) {
                        Gui.showPopup('ErrorPopup', {
                            title: _t('Transaction in progress'),
                            body: _t('Please process or cancel the current transaction.'),
                        });
                } else {
                    return super.__showScreen(...arguments);
                }
            }

            connect_to_proxy() {
                this.env.proxy.ping_boxes();
                if (this.env.pos.config.iface_scan_via_proxy) {
                    this.env.barcode_reader.connect_to_proxy();
                }
                if (this.env.pos.config.iface_print_via_proxy) {
                    this.env.proxy.connect_to_printer();
                }
                if (!this.env.proxy.status_loop_running) {
                    this.env.proxy.status_loop();
                }
                return Promise.resolve();
            }
        };

    Registries.Component.extend(Chrome, PosIoTChrome);

    return PosIoTChrome;
});
