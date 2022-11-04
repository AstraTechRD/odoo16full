odoo.define('pos_settle_due.PartnerLine', function (require) {
    'use strict';

    const PartnerLine = require('point_of_sale.PartnerLine');
    const Registries = require('point_of_sale.Registries');

    const POSSettleDuePartnerLine = (PartnerLine) =>
        class extends PartnerLine {
            getPartnerLink() {
                return `/web#model=res.partner&id=${this.props.partner.id}`;
            }
            async settlePartnerDue(event) {
                if (this.props.selectedPartner == this.props.partner) {
                    event.stopPropagation();
                }
                const totalDue = this.props.partner.total_due;
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
                this.trigger('discard'); // make sure the PartnerListScreen resolves and properly closed.
                const newOrder = this.env.pos.add_new_order();
                const payment = newOrder.add_paymentline(selectedPaymentMethod);
                payment.set_amount(totalDue);
                newOrder.set_partner(this.props.partner);
                this.showScreen('PaymentScreen');
            }
        };

    Registries.Component.extend(PartnerLine, POSSettleDuePartnerLine);

    return PartnerLine;
});
