odoo.define('pos_iot.payment', function (require) {
"use strict";

var core = require('web.core');
var PaymentInterface = require('point_of_sale.PaymentInterface');
const { Gui } = require('point_of_sale.Gui');

var _t = core._t;

var PaymentIOT = PaymentInterface.extend({
    get_terminal() {
        return this.payment_method.terminal_proxy;
    },

    send_payment_request: function (cid) {
        var self = this;
        this._super.apply(this, this.arguments);
        const terminal_proxy = self.get_terminal();

        if (!terminal_proxy) {
            this._showErrorConfig();
            return Promise.resolve(false);
        }

        return new Promise(function (resolve) {
            self._waitingResponse = self._waitingPayment;
            terminal_proxy.add_listener(self._onValueChange.bind(self, resolve, self.pos.get_order()));
            self._send_request(self.get_payment_data(cid));
        });
    },

    get_payment_data: function (cid) {
        var paymentline = this.pos.get_order().get_paymentline(cid);
        return {
            messageType: 'Transaction',
            TransactionID: parseInt(this.pos.get_order().uid.replace(/-/g, '')),
            cid: cid,
            amount: Math.round(paymentline.amount*100),
        };
    },

    send_payment_cancel: function (order, cid) {
        var self = this;
        var terminal = this.get_terminal();
        if (terminal) {
            this._super.apply(this, this.arguments);
            var data = {
                messageType: 'Cancel',
                reason: 'manual'
            };
            return new Promise(function (resolve) {
                self._waitingResponse = self._waitingCancel;
                terminal.add_listener(self._onValueChange.bind(self, resolve, order));
                self._send_request(data);
            });
        }
        return Promise.reject();
    },

    // extra private methods
    _send_request: function (data) {
        var self = this;
        this.get_terminal().action(data)
            .then(self._onActionResult.bind(self))
            .guardedCatch(self._onActionFail.bind(self));
    },
    _onActionResult: function (data) {
        if (data.result === false) {
            Gui.showPopup('ErrorPopup',{
                'title': _t('Connection to terminal failed'),
                'body':  _t('Please check if the terminal is still connected.'),
            });
            if (this.pos.get_order().selected_paymentline) {
                this.pos.get_order().selected_paymentline.set_payment_status('force_done');
            }
        }
    },
    _onActionFail: function () {
        Gui.showPopup('ErrorPopup',{
            'title': _t('Connection to IoT Box failed'),
            'body':  _t('Please check if the IoT Box is still connected.'),
        });
        if (this.pos.get_order().selected_paymentline) {
            this.pos.get_order().selected_paymentline.set_payment_status('force_done');
        }
    },
    _showErrorConfig: function () {
        Gui.showPopup('ErrorPopup',{
            'title': _t('Configuration of payment terminal failed'),
            'body':  _t('You must select a payment terminal in your POS config.'),
        });
    },

    _waitingPayment: function (resolve, data, line) {
        if (data.Error) {
            Gui.showPopup('ErrorPopup',{
                'title': _t('Payment terminal error'),
                'body':  _t(data.Error),
            });
            this.get_terminal().remove_listener();
            resolve(false);
        } else if (data.Response === 'Approved') {
            this.get_terminal().remove_listener();
            resolve(true);
        } else if (['WaitingForCard', 'WaitingForPin'].includes(data.Stage)) {
            line.set_payment_status('waitingCard');
        }
    },

    _waitingCancel: function (resolve, data) {
        if (data.Stage === 'Finished' || data.Error) {
            this.get_terminal().remove_listener();
            resolve(true);
        }
    },

    /**
     * Function ran when Device status changes.
     *
     * @param {Object} data.Response
     * @param {Object} data.Stage
     * @param {Object} data.Ticket
     * @param {Object} data.device_id
     * @param {Object} data.owner
     * @param {Object} data.session_id
     * @param {Object} data.value
     * @param {Object} data.Card
     */
    _onValueChange: function (resolve, order, data) {
        var line = order.get_paymentline(data.cid);
        var terminal_proxy = this.pos.payment_methods_by_id[line.payment_method.id].terminal_proxy;
        if (line && terminal_proxy && (!data.owner || data.owner === this.pos.env.services.iot_longpolling._session_id)) {
            this._waitingResponse(resolve, data, line);
            if (data.Ticket) {
                line.set_receipt_info(data.Ticket.replace(/\n/g, "<br />"));
            }
            if (data.Card) {
                line.card_type = data.Card;
            }
        }
    },
});

var PaymentWorldline = PaymentIOT.extend({
    send_payment_cancel: function (order, cid) {
        if (this.get_terminal()) {
            this._send_request({ messageType: 'Cancel' });
        }

        return new Promise((resolve) => {
            this.cancel_resolve = resolve;
        });
    },

    send_payment_request: function (cid) {
        var paymentline = this.pos.get_order().get_paymentline(cid);
        paymentline.transaction_id = Math.floor(Math.random() * Math.pow(2, 32)); // 4 random bytes
        return this._super.apply(this, arguments);
    },

    get_payment_data: function (cid) {
        var data = this._super.apply(this, arguments);
        data.actionIdentifier = this.pos.get_order().get_paymentline(cid).transaction_id;
        return data;
    },

    _waitingPayment: function (resolve, data, line) {
        if (data.Stage == 'Cancel') {
            // Result of a cancel request
            if (data.Error) {
                // Cancel failed, wait for transaction response
                this.cancel_resolve(false);
                line.set_payment_status('waitingCard');
                Gui.showPopup('ErrorPopup', {
                    'title': _t('Transaction could not be cancelled'),
                    'body':  data.Error,
                });
            } else {
                this.get_terminal().remove_listener();
                this.cancel_resolve(true);
                resolve(false);
            }
        } else if (data.Disconnected) {
            // Terminal disconnected
            line.set_payment_status('force_done');
            Gui.showPopup('ErrorPopup', {
                'title': _t('Terminal Disconnected'),
                'body':  _t('Please check the network connection and then check the status of the last transaction manually.'),
            });
        } else if (line.payment_status !== 'retry') {
            // Result of a transaction
            return this._super.apply(this, arguments);
        }
    },
});


return {
    PaymentIngenico: PaymentIOT,
    PaymentWorldline: PaymentWorldline,
};
});
