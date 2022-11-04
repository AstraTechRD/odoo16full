/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BankRecKanbanView } from "@account_accountant/components/bank_reconciliation/bank_rec_widget_kanban";
import { BankRecWidgetRejectDialog } from "./bank_rec_widget_batch_reject_dialog";

export class BankRecKanbanControllerBatch extends BankRecKanbanView.Controller {

    async performAction(action_data) {
        if (["ir.actions.client", "ir.actions.act_window"].includes(action_data.type) && action_data.target === 'new') {
            this.env.services.dialog.add(
                BankRecWidgetRejectDialog,
                {
                    resModel: action_data.res_model,
                    context: action_data.context,
                    title: action_data.name,
                    kanbanActionFn: super.performAction.bind(this),
                }
            );
        } else {
            super.performAction(action_data);
        }
    }
}

export const BankRecKanbanViewBatch = {
    ...BankRecKanbanView,
    Controller: BankRecKanbanControllerBatch,
};

registry.category("views").add('bank_rec_widget_kanban', BankRecKanbanViewBatch, { force: true });
