odoo.define('l10n_de_pos_res_cert.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const PosDeResPaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        async _finalizeValidation() {
            if (this.env.pos.isRestaurantCountryGermanyAndFiskaly()) {
                try {
                    await this.currentOrder.retrieveAndSendLineDifference()
                } catch (_e) {
                    // do nothing with the error
                }
            }
            await super._finalizeValidation(...arguments);
        }
    };

    Registries.Component.extend(PaymentScreen, PosDeResPaymentScreen);

    return PosDeResPaymentScreen;
});
