/** @odoo-module **/

import { registry } from "@web/core/registry";

import { BankRecWidgetFormInnerTabAmls } from "@account_accountant/components/bank_reconciliation/bank_rec_widget_form_inner_tab_amls";

export class BankRecWidgetFormInnerTabBatchPaymentsRenderer extends BankRecWidgetFormInnerTabAmls.Renderer {
    getRowClass(record) {
        const classes = super.getRowClass(record);
        if (this.selectedBatchPaymentIDs.includes(record.resId)){
            return `${classes} o_rec_widget_list_selected_item`;
        }
        return classes;
    }
    get selectedBatchPaymentIDs() {
        return this.props.bankRecRecord.data.selected_batch_payment_ids.records.map(r => r.data.id);
    }
    async onCellClicked(record, column, ev) {
        this.props.bankRecRecord.update({todo_command: `add_new_batch_payment,${record.resId}`});

    }

}
BankRecWidgetFormInnerTabBatchPaymentsRenderer.props = [
    ...BankRecWidgetFormInnerTabAmls.Renderer.props,
    "bankRecRecord?",
]

export const BankRecWidgetFormInnerTabBatchPayments = {
    ...BankRecWidgetFormInnerTabAmls,
    Renderer: BankRecWidgetFormInnerTabBatchPaymentsRenderer,
}

registry.category("views").add("bank_rec_widget_form_batch_payments_list", BankRecWidgetFormInnerTabBatchPayments);
