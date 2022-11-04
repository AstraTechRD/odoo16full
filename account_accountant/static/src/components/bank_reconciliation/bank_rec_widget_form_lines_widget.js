/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component, useState } = owl;

export class BankRecWidgetFormLinesWidget extends Component {
    setup() {
        this.state = useState({
            extraNoteVisible: false,
        });
    }
    range(n) {
        return [...Array(Math.max(n, 0)).keys()];
    }

    /** Create the data to render the template **/
    getRenderValues() {
        let data = this.props.record.data.lines_widget;

        // Prepare columns.
        let columns = [
            ["account", this.env._t("Account")],
            ["partner", this.env._t("Partner")],
            ["date", this.env._t("Date")],
            ["label", this.env._t("Label")],
        ];
        if(data.display_analytic_account_column){
            columns.push(["analytic_account", this.env._t("Analytic Account")]);
        }
        if(data.display_multi_currency_column){
            columns.push(["amount_currency", this.env._t("Amount in Currency")], ["currency", this.env._t("Currency")]);
        }
        if(data.display_taxes_column){
            columns.push(["taxes", this.env._t("Taxes")]);
        }
        columns.push(["debit", this.env._t("Debit")], ["credit", this.env._t("Credit")], ["__trash", ""]);

        return {...data, columns: columns}
    }

    /** The user clicked on a row **/
    mountLine(ev, lineIndex, clickedColumn=null) {
        if (this.props.record.data.state === "reconciled") {
            return;
        }
        if (!clickedColumn && ev.target.attributes && ev.target.attributes.field) {
            clickedColumn = ev.target.attributes['field'].value;
        }
        if (lineIndex != this.props.record.data.form_index) {
            let command = `mount_line_in_edit,${lineIndex}`;
            if (clickedColumn) {
                command = `${command},${clickedColumn}`;
            }
            this.props.record.update({todo_command: command});
        } else if (clickedColumn) {
            this.props.record.update({ next_action_todo: { type: 'focus', field: clickedColumn}})
        }
    }

    /** The user clicked on the trash button **/
    async removeLine(lineIndex) {
        await this.props.record.update({todo_command: `remove_line,${lineIndex}`})
    }

    /** The user clicked on the link to see the journal entry details **/
    async showMove(move_id) {
        await this.props.record.update({todo_command: `button_clicked,button_form_redirect_to_move_form,${move_id}`});
        this.env.kanbanDoAction(this.props.record.data.next_action_todo);
    }

}
BankRecWidgetFormLinesWidget.template = "account_accountant.bank_rec_widget_form_lines_widget";
BankRecWidgetFormLinesWidget.props = {
    ...standardFieldProps,
}

registry.category("fields").add("bank_rec_widget_form_lines_widget", BankRecWidgetFormLinesWidget);
