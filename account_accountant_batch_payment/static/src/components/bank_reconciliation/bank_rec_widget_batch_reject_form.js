/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

export class BankRecBatchRejectFormController extends FormController {
    /**
     * @override
     */
    async afterExecuteActionButton(clickParams) {
        await this.model.root.load();
        if (!this.model.root.data.cancel_action_todo) {
            this.props.kanbanDoAction(this.model.root.data.next_action_todo);
        }
        this.props.dialogCloseFn();
    }
}
BankRecBatchRejectFormController.props = {
    ...FormController.props,
    kanbanDoAction: { type: Function, optional: true },
    dialogCloseFn: { type: Function, optional: true },
}

export const BankRecBatchForm = {
    ...formView,
    Controller: BankRecBatchRejectFormController,
}

registry.category("views").add('bank_rec_batch_reject_wizard', BankRecBatchForm);
