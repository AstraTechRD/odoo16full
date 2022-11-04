odoo.define('l10n_de_pos_cert.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const PosDePaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        setup() {
            super.setup();
            if (this.env.pos.isCountryGermanyAndFiskaly()) {
                const _super_handlePushOrderError = this._handlePushOrderError.bind(this);
                this._handlePushOrderError = async (error) => {
                    if (error.code === 'fiskaly') {
                        const message = {
                            'noInternet': this.env._t('Cannot sync the orders with Fiskaly !'),
                            'unknown': this.env._t('An unknown error has occurred ! Please contact Odoo for more information.')
                        };
                        this.trigger('fiskaly-error', {error, message});
                    } else {
                        _super_handlePushOrderError(error);
                    }
                }
                this.validateOrderFree = true;
            }
        }
        //@override
        async validateOrder(isForceValidate) {
            if (this.env.pos.isCountryGermanyAndFiskaly()) {
                if (this.validateOrderFree) {
                    this.validateOrderFree = false;
                    try {
                        await super.validateOrder(...arguments);
                    } finally {
                        this.validateOrderFree = true;
                    }
                }
            } else {
                await super.validateOrder(...arguments);
            }
        }
        //@override
        async _finalizeValidation() {
            if (this.env.pos.isCountryGermanyAndFiskaly()) {
                if (this.currentOrder.isTransactionInactive()) {
                    try {
                        await this.currentOrder.createTransaction();
                    } catch (error) {
                        if (error.status === 0) {
                            this.trigger('fiskaly-no-internet-confirm-popup', super._finalizeValidation.bind(this));
                        } else {
                            const message = {'unknown': this.env._t('An unknown error has occurred ! Please, contact Odoo.')};
                            this.trigger('fiskaly-error', {error, message});
                        }
                    }
                }
                if (this.currentOrder.isTransactionStarted()) {
                    try {
                        await this.currentOrder.finishShortTransaction();
                        await super._finalizeValidation(...arguments)
                    } catch (error) {
                        if (error.status === 0) {
                            this.trigger('fiskaly-no-internet-confirm-popup', super._finalizeValidation.bind(this));
                        } else {
                            const message = {'unknown': this.env._t('An unknown error has occurred ! Please, contact Odoo.')};
                            this.trigger('fiskaly-error', {error, message});
                        }
                    }
                }
            }
            else {
                await super._finalizeValidation(...arguments);
            }
        }
    };

    Registries.Component.extend(PaymentScreen, PosDePaymentScreen);

    return PaymentScreen;
});
