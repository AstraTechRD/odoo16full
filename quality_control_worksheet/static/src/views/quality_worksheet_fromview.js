/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Record, RelationalModel } from "@web/views/basic_relational_model";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

class WorksheetValidationController extends FormController {
    async discard() {
        await super.discard();
        const record = this.model.root.data;
        const context = this.model.root.context;
        const action = await this.model.orm.call(
            "quality.check",
            "action_worksheet_discard",
            [record.x_quality_check_id[0]],
            { context }
        );
        this.model.actionService.doAction(action);
    }
}

class WorksheetValidationRecord extends Record {
    async save() {
        const res = await super.save(...arguments);
        // after studio exit, although the mode is readonly, the save button is visible
        if (this.mode != "readonly") {
            const action = await this.model.ormService.call(
                "quality.check",
                "action_worksheet_check",
                [this.data.x_quality_check_id[0]],
                { context: this.context }
            );
            this.model.actionService.doAction(action);
        }
        return res;
    }
}

class WorksheetValidationModel extends RelationalModel {
    get canBeAbandoned() {
        return false;
    }
}
WorksheetValidationModel.Record = WorksheetValidationRecord;

export const WorksheetValidationFormView = {
    ...formView,
    Controller: WorksheetValidationController,
    Model: WorksheetValidationModel,
};

registry.category("views").add("worksheet_validation", WorksheetValidationFormView);
