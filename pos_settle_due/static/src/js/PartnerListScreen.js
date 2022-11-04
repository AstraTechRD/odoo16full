odoo.define('pos_settle_due.PartnerListScreen', function (require) {
    'use strict';

    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
    const Registries = require('point_of_sale.Registries');

    const POSSettleDuePartnerListScreen = (PartnerListScreen) =>
        class extends PartnerListScreen {
            setup() {
                super.setup();
            }
            get isBalanceDisplayed() {
                return true;
            }
            get partnerLink() {
                return `/web#model=res.partner&id=${this.state.editModeProps.partner.id}`;
            }
            async settleCustomerDue() {
                let updatedDue = await this.env.pos.refreshTotalDueOfPartner(this.state.editModeProps.partner);
                const totalDue = updatedDue ? updatedDue[0].total_due : this.state.editModeProps.partner.total_due;
                const paymentMethods = this.env.pos.payment_methods.filter(
                    (method) => this.env.pos.config.payment_method_ids.includes(method.id) && method.type != 'pay_later'
                );
                const selectionList = paymentMethods.map((paymentMethod) => ({
                    id: paymentMethod.id,
                    label: paymentMethod.name,
                    item: paymentMethod,
                }));
                const { confirmed, payload: selectedPaymentMethod } = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Select the payment method to settle the due'),
                    list: selectionList,
                });
                if (!confirmed) return;
                this.state.selectedPartner = this.state.editModeProps.partner;
                this.confirm(); // make sure the PartnerListScreen resolves and properly closed.

                // Reuse an empty order that has no partner or has partner equal to the selected partner.
                let newOrder;
                const emptyOrder = this.env.pos.orders.find(
                    (order) =>
                        order.orderlines.length === 0 &&
                        order.paymentlines.length === 0 &&
                        (!order.partner || order.partner.id === this.state.selectedPartner.id)
                );
                if (emptyOrder) {
                    newOrder = emptyOrder;
                    // Set the empty order as the current order.
                    this.env.pos.set_order(newOrder);
                } else {
                    newOrder = this.env.pos.add_new_order()
                }
                const payment = newOrder.add_paymentline(selectedPaymentMethod);
                payment.set_amount(totalDue);
                newOrder.set_partner(this.state.selectedPartner);
                this.showScreen('PaymentScreen');
            }
        };

    Registries.Component.extend(PartnerListScreen, POSSettleDuePartnerListScreen);

    return PartnerListScreen;
});
