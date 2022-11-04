odoo.define('pos_settle_due.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const { float_is_zero } = require('web.utils');

    const PosSettleDuePaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            //@override
            async validateOrder(isForceValidate) {
                const order = this.currentOrder;
                const change = order.get_change();
                const paylaterPaymentMethod = this.env.pos.payment_methods.filter(
                    (method) =>
                        this.env.pos.config.payment_method_ids.includes(method.id) && method.type == 'pay_later'
                )[0];
                const existingPayLaterPayment = order
                    .get_paymentlines()
                    .find((payment) => payment.payment_method.type == 'pay_later');
                if (
                    order.get_orderlines().length === 0 &&
                    !float_is_zero(change, this.env.pos.currency.decimal_places) &&
                    paylaterPaymentMethod &&
                    !existingPayLaterPayment
                ) {
                    const partner = order.get_partner();
                    if (partner) {
                        const { confirmed } = await this.showPopup('ConfirmPopup', {
                            title: this.env._t('The order is empty'),
                            body: _.str.sprintf(
                                this.env._t('Do you want to deposit %s to %s?'),
                                this.env.pos.format_currency(change),
                                order.get_partner().name
                            ),
                            confirmText: this.env._t('Yes'),
                        });
                        if (confirmed) {
                            const paylaterPayment = order.add_paymentline(paylaterPaymentMethod);
                            paylaterPayment.set_amount(-change);
                            return super.validateOrder(...arguments);
                        }
                    } else {
                        const { confirmed } = await this.showPopup('ConfirmPopup', {
                            title: this.env._t('The order is empty'),
                            body: _.str.sprintf(
                                this.env._t(
                                    'Do you want to deposit %s to a specific customer? If so, first select him/her.'
                                ),
                                this.env.pos.format_currency(change)
                            ),
                            confirmText: this.env._t('Yes'),
                        });
                        if (confirmed) {
                            const { confirmed: confirmedPartner, payload: newPartner } = await this.showTempScreen(
                                'PartnerListScreen'
                            );
                            if (confirmedPartner) {
                                order.set_partner(newPartner);
                            }
                            const paylaterPayment = order.add_paymentline(paylaterPaymentMethod);
                            paylaterPayment.set_amount(-change);
                            return super.validateOrder(...arguments);
                        }
                    }
                } else {
                    return super.validateOrder(...arguments);
                }
            }
            async _finalizeValidation() {
                await super._finalizeValidation(...arguments);
                const hasCustomerAccountAsPaymentMethod = this.currentOrder.get_paymentlines().find(
                    paymentline => paymentline.payment_method.type === 'pay_later'
                );
                if (hasCustomerAccountAsPaymentMethod) {
                    this.env.pos.refreshTotalDueOfPartner(this.currentOrder.get_partner());
                }
            }
        };

    Registries.Component.extend(PaymentScreen, PosSettleDuePaymentScreen);

    return PaymentScreen;
});

