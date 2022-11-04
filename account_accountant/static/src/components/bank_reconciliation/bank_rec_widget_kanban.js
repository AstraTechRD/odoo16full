/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CallbackRecorder } from "@web/webclient/actions/action_hook";

import { View } from "@web/views/view";
import { useSetupView } from "@web/views/view_hook";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

import { BankRecWidgetGlobalInfo } from "./bank_rec_widget_global_info";

const { useState, useSubEnv, useRef, useChildSubEnv } = owl;

export class BankRecKanbanRecord extends KanbanRecord {
    getRecordClasses() {
        let classes = `${super.getRecordClasses()} w-100 o_bank_rec_st_line`;
        if (this.props.record.resId === this.props.selectedStLineId) {
            classes = `${classes} o_bank_rec_selected_st_line`;
        }
        return classes;
    }
}
BankRecKanbanRecord.props = [
    ...KanbanRecord.props,
    "selectedStLineId?",
]

BankRecKanbanRecord.template = "account.BankRecKanbanRecord";

export class BankRecKanbanController extends KanbanController {
    async setup() {
        super.setup();

        // we don't care about subview states but we want to avoid them to record
        // some callbacks in the BankRecKanbanController callback recorders passed
        // by the action service
        useChildSubEnv({
            __beforeLeave__: new CallbackRecorder(),
            __getLocalState__: new CallbackRecorder(),
            __getGlobalState__: new CallbackRecorder(),
            __getContext__: new CallbackRecorder(),
        });

        this.default_journal_id = this.props.context.default_journal_id;
        this.state = useState({
            selectedStLineId: null,
        });

        this.orm = useService("orm");
        this.action = useService("action");
        useSubEnv({
            kanbanDoAction: this.performAction.bind(this),
        });
        const rootRef = useRef("root");
        useSetupView({
            rootRef,
            getLocalState: () => {
                return {
                    lastStLineId: this.state.selectedStLineId,
                };
            },
        });
        // to avoid a flicker we call recordsLoaded only when the model is ready
        this.model.addEventListener("update", () => this.recordsLoaded(), { once: true });
        this.env.searchModel.addEventListener("update", () => this.userSearched());
    }

    userSearched() {
        this.model.addEventListener("update", () => this.recordsLoaded(), { once: true });
    }

    get bankRecFormViewProps() {
        return {
            type: "form",
            views: [[false, "form"]],
            context: {
                form_view_ref: "account_accountant.view_bank_rec_widget_form",
                default_st_line_id: this.state.selectedStLineId,
                default_todo_command: this.props.context.default_todo_command || 'trigger_matching_rules',
            },
            display: { controlPanel: false, noBreadcrumbs: true, },
            mode: "edit",
            resModel: "bank.rec.widget",
        }
    }

    recordsLoaded() {
        if (this.props.state && this.props.state.lastStLineId) {
            this.selectStLine(this.props.state.lastStLineId);
            this.props.state.lastStLineId = null;
        } else if (this.props.context.default_st_line_id) {
            this.selectStLine(this.props.context.default_st_line_id);
        } else {
            this.selectStLine(this.getNextAvailableStLine());
        }
        if (!this.default_journal_id && this.state.selectedStLineId) {
            this.default_journal_id = this.recordById(this.state.selectedStLineId).data.journal_id[0];
        }
    }

    get stLineIdsStillToReconcile() {
        return this.records.filter((record) => (!record.data.is_reconciled || record.data.to_check)).map((record) => record.resId);
    }

    getNextAvailableStLine(afterStLineId=null) {
        let waitBeforeReturn = Boolean(afterStLineId);
        for (const stLineId of this.stLineIdsStillToReconcile) {
            if (waitBeforeReturn) {
                if (stLineId === afterStLineId) {
                    waitBeforeReturn = false;
                }
            } else {
                return stLineId;
            }
        }
        return null;
    }

    async selectStLine(stLineId){
        const isSameStLine = this.state.selectedStLineId && this.state.selectedStLineId === stLineId;
        if (!isSameStLine) {
            this.state.selectedStLineId = stLineId;
        }
    }

    async reload() {
        await this.model.root.load();
        this.model.notify();
    }

    recordById(id) {
        return this.records.find((record) => record.data.id === id);
    }

    get records() {
        return this.model.root.records;
    }

    async openRecord(record, mode) {
        this.selectStLine(record.resId);
    }

    async performAction(action_data) {
        if (["ir.actions.client", "ir.actions.act_window"].includes(action_data.type)) {
            await this.action.doAction(action_data);
        } else if (action_data.type === "rpc") {
            this.orm.call("bank.rec.widget", action_data.method, [[], action_data.st_line_id, action_data.params], {}).then(() => {
                this.reload();
            });
            const nextStLineId = this.getNextAvailableStLine(action_data.st_line_id);
            this.selectStLine(nextStLineId);
        } else if (action_data.type === "move_to_next") {
            this.reload();
            const nextStLineId = this.getNextAvailableStLine(action_data.st_line_id);
            this.selectStLine(nextStLineId);
        } else if (action_data.type === "refresh" || !action_data) {
            await this.reload();
        }
    }
}
BankRecKanbanController.template = "account.BankReconKanbanController";
BankRecKanbanController.components = {
    ...BankRecKanbanController.components,
    BankRecWidgetGlobalInfo,
    View,
}

export class BankRecKanbanRenderer extends KanbanRenderer {}
BankRecKanbanRenderer.template = "account.BankRecKanbanRenderer";
BankRecKanbanRenderer.props = [
    ...KanbanRenderer.props,
    "selectedStLineId?",
]
BankRecKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: BankRecKanbanRecord,
}

export const BankRecKanbanView = {
    ...kanbanView,
    Controller: BankRecKanbanController,
    Renderer: BankRecKanbanRenderer,
    buttonTemplate: "account.BankRecKanbanRenderer.Buttons",
    searchMenuTypes: ["filter"],
};

registry.category("views").add('bank_rec_widget_kanban', BankRecKanbanView);
