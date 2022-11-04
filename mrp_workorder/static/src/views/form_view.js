/** @odoo-module */

import { registry } from "@web/core/registry";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useBus } from "@web/core/utils/hooks";

import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

const { useRef } = owl;

export class WorkorderFormController extends FormController {
    setup() {
        super.setup();
        this.workorderBus = this.props.workorderBus;
        useBus(this.workorderBus, "force_save_workorder", async (ev) => {
            if (this.model.root.resModel === "mrp.workorder") {
                await this.model.root.save({ stayInEdition: true });
                ev.detail.resolve();
            }
        });
        useBus(this.workorderBus, "force_save_check", async (ev) => {
            if (this.model.root.resModel === "quality.check") {
                await this.model.root.save({ stayInEdition: true });
                ev.detail.resolve();
            }
        });
        const rootRef = useRef("root");
        // before executing button action
        const beforeExecuteAction = async (params) => {
            await this.model.root.save({ stayInEdition: true });
            if (params.type && params.type === "workorder_event") {
                this.workorderBus.trigger("workorder_event", params.name);
                return false;
            }
            if (this.model.root.resModel === "mrp.workorder") {
                if (this.model.root.data.current_quality_check_id) {
                    await new Promise((resolve) =>
                        this.workorderBus.trigger("force_save_check", { resolve })
                    );
                }
            }
            if (this.model.root.resModel === "quality.check") {
                await new Promise((resolve) =>
                    this.workorderBus.trigger("force_save_workorder", { resolve })
                );
            }
        };
        // after executing button action
        const reload = () => this.workorderBus.trigger("refresh");
        useViewButtons(this.model, rootRef, { beforeExecuteAction, reload });
    }
}

WorkorderFormController.props = {
    ...FormController.props,
    workorderBus: Object,
};
registry.category("views").add("workorder_form", {
    ...formView,
    Controller: WorkorderFormController,
});
