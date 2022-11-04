/** @odoo-module **/

import { registry } from "@web/core/registry";

import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormCompiler } from "@web/views/form/form_compiler";
import { formView } from "@web/views/form/form_view";
import { Notebook } from  "@web/core/notebook/notebook"

const { useSubEnv, useEffect, useRef, onPatched } = owl;

export class BankRecWidgetFormController extends FormController {
    setup() {
        super.setup();
        useSubEnv({
            onClickViewButton: this.viewButtonClick.bind(this),
        });
    }

    displayName() {
        return this.env._t("Bank Reconciliation");
    }

    async viewButtonClick({ clickParams }) {
        await this.model.root.update({todo_command: `button_clicked,${clickParams.name}`});
        this.env.kanbanDoAction(this.model.root.data.next_action_todo);
    }

    beforeUnload() {
        return;
    }
}
BankRecWidgetFormController.props = {
    ...FormController.props,
    // The views are needed because when loading the form view, owl tries to use it and if it is not available it
    // falls back to the action's views ending up in rendering wrong list view
    views: { optional: true },
}

export class BankRecNotebook extends Notebook {
    setup() {
        super.setup();
        useEffect(
            () => this.callOnTabChange(),
            () => [this.state.currentPage]
        );
        useEffect(
            () => this.activateTab(),
            () => [this.props.selectedLine]
        );
    }

    get manualOperationsPage() {
        return this.pages.find((p) => p[1].name === "manual_operations_tab");
    }

    get isManualOperationsTabSelected() {
        return this.state.currentPage && this.state.currentPage === this.manualOperationsPage[0];
    }

    callOnTabChange() {
        if (this.props.onTabChange && this.state.currentPage && this.props.slots[this.state.currentPage]) {
            this.props.onTabChange(this.props.slots[this.state.currentPage].name);
        }
    }

    activateTab() {
        if (this.props.selectedLine) {
            if (!this.isManualOperationsTabSelected) {
                this.state.currentPage = this.manualOperationsPage[0];
            }
        } else if (this.isManualOperationsTabSelected) {
            this.state.currentPage = this.pages[0][0];
        }
    }
}
BankRecNotebook.props = {
    ...Notebook.props,
    selectedLine: { optional: true },
    onTabChange: { type: Function, optional: true },
}

export class BankRecFormRenderer extends FormRenderer {
    setup() {
        super.setup();
        onPatched(this.nextActionChanged);
        this.rootRef = useRef("compiled_view_root");
    }
    async notebookTabChanged(tabName) {
        const lastLineIndex = this.props.record.data.lines_widget.lines.slice(-1)[0].index.value;
        if (tabName === "manual_operations_tab") {
            if (!this.currentLine) {
                await this.props.record.update({todo_command: `mount_line_in_edit,${lastLineIndex},debit`});
            } else {
                this.nextActionChanged();
            }
        } else if (this.currentLine) {
            await this.props.record.update({todo_command: "clear_edit_form"});
        }
    }

    get currentLine() {
        return this.props.record.data.form_index;
    }

    nextActionChanged() {
        // process next_action_todo if it is of type focus
        if (this.props.record.data.next_action_todo.type === 'focus') {
            this.focusField(this.props.record.data.next_action_todo.field);
        }
    }

    focusField(field) {
        if (['debit', 'credit'].includes(field)) {
            if (this.focusElement("div[name='form_balance'] input")) {
                return;
            }
            if (this.focusElement("div[name='form_amount_currency'] input")) {
                return;
            }
        } else {
            if (this.focusElement(`div[name='form_${field}'] input`)) {
                return;
            }
            if (this.focusElement(`input[name='form_${field}']`)) {
                return;
            }
        }
    }

    focusElement(selector) {
        let inputEl = this.rootRef.el.querySelector(selector);
        if (!inputEl) {
            return false;
        }

        if (inputEl.tagName === "INPUT") {
            inputEl.focus();
            inputEl.select();
        } else {
            inputEl.focus();
        }
        return true;
    }
}
BankRecFormRenderer.components = {
    ...FormRenderer.components,
    Notebook: BankRecNotebook,
}

export class BankRecFormCompiler extends FormCompiler {
    compileNotebook(el, params) {
        const noteBook = super.compileNotebook(...arguments);
        noteBook.setAttribute("onTabChange.bind", "notebookTabChanged");
        noteBook.setAttribute("selectedLine", "this.currentLine");
        return noteBook;
    }
}

export const BankRecWidgetForm = {
    ...formView,
    Controller: BankRecWidgetFormController,
    Compiler: BankRecFormCompiler,
    Renderer: BankRecFormRenderer,
    display: { controlPanel: false },
}

registry.category("views").add('bank_rec_widget_form', BankRecWidgetForm);
