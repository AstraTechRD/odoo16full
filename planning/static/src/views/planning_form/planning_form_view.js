/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { Record, RelationalModel } from "@web/views/basic_relational_model";

const { markup, onMounted } = owl;


class PlanningFormRecord extends Record {
    async save() {
        const dirtyFields = this.dirtyFields.map((f) => f.name);
        const res = await super.save(...arguments);

        if (dirtyFields.includes("repeat") && this.data["repeat"]) {
            const message = this.model.env._t("The recurring shifts have successfully been created.");
            this.model.notificationService.add(
                markup(
                    `<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(message)}</span>`
                ),
                { type: "success" }
            );
        }
        return res;
    }
}

class PlanningFormModel extends RelationalModel {}
PlanningFormModel.Record = PlanningFormRecord;

export class PlanningFormController extends FormController {

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        onMounted(() => {
            this.initialTemplateCreation = this.model.root.data.template_creation;
        });
    }

    async beforeExecuteActionButton(clickParams) {
        const resId = this.model.root.resId;
        if (clickParams.name === "unlink") {
            const canProceed = await new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    body: this.env._t("Are you sure you want to delete this shift?"),
                    cancel: () => resolve(false),
                    close: () => resolve(false),
                    confirm: () => resolve(true),
                });
            });
            if (!canProceed) {
                return false;
            }
        } else if (clickParams.name === 'action_send' && resId) {
            // We want to check if all employees impacted to this action have a email.
            // For those who do not have any email in work_email field, then a FormViewDialog is displayed for each employee who is not email.
            const result = await this.orm.call(this.props.resModel, "get_employees_without_work_email", [resId]);
            if (result) {
                const { res_ids: resIds, relation: resModel, context } = result;
                const canProceed = await this.displayDialogWhenEmployeeNoEmail(resIds, resModel, context);
                if (!canProceed) {
                    return false;
                }
            }
        }
        const templateCreation = this.model.root.data.template_creation;
        if (!this.initialTemplateCreation && templateCreation) {
            // then the shift should be saved as a template too.
            const message = this.env._t("This shift was successfully saved as a template.");
            this.notification.add(
                markup(`<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(message)}</span>`),
                { type: "success" },
            );
        }
        return super.beforeExecuteActionButton(clickParams);
    }

    /**
     * Display a dialog form view of employee model for each employee who has no work email.
     *
     * @param {Array<number>} resIds the employee ids without work email.
     * @param {string} resModel the model name to display the form view.
     * @param {Object} context context.
     *
     * @returns {Promise}
     */
    async displayDialogWhenEmployeeNoEmail(resIds, resModel, context) {
        const results = await Promise.all(resIds.map((resId) => {
            return new Promise((resolve) => {
                this.dialogService.add(FormViewDialog, {
                    title: "",
                    resModel,
                    resId,
                    context,
                    preventCreate: true,
                    onRecordSaved: () => resolve(true),
                }, { onClose: () => resolve(false) });
            });
        }));
        return results.every((r) => r);
    }
}

export const planningFormView = {
    ...formView,
    Controller: PlanningFormController,
    Model: PlanningFormModel,
};

registry.category("views").add("planning_form", planningFormView);
