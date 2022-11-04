/** @odoo-module **/

import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";


export class BankRecWidgetFormInnerTabAmlsRenderer extends ListRenderer {
    getRowClass(record) {
        const classes = super.getRowClass(record);
        if (this.selectedAmlIDs.includes(record.resId)){
            return `${classes} o_rec_widget_list_selected_item`;
        }
        return classes;
    }

    get selectedAmlIDs() {
        return this.props.bankRecRecord.data.selected_aml_ids.records.map(r => r.data.id);
    }

    async onCellClicked(record, column, ev) {
        if (this.selectedAmlIDs.includes(record.resId)) {
            this.props.bankRecRecord.update({todo_command: `remove_new_aml,${record.resId}`});
        } else {
            this.props.bankRecRecord.update({todo_command: `add_new_amls,${record.resId}`});
        }
    }
}
BankRecWidgetFormInnerTabAmlsRenderer.props = [
    ...ListRenderer.props,
    "bankRecRecord?",
]

export class BankRecWidgetFormInnerTabAmlsController extends ListController {}
BankRecWidgetFormInnerTabAmlsController.template = "account_accountant.BankRecWidgetFormInnerTabAmlsController";
BankRecWidgetFormInnerTabAmlsController.props = {
    ...ListController.props,
    bankRecRecord: { type: Object, optional: true },
}

export const BankRecWidgetFormInnerTabAmls = {
    ...listView,
    Controller: BankRecWidgetFormInnerTabAmlsController,
    Renderer: BankRecWidgetFormInnerTabAmlsRenderer,
}

registry.category("views").add("bank_rec_widget_form_amls_list", BankRecWidgetFormInnerTabAmls);
