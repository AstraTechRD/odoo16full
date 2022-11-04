/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;

export class BankRecWidgetHTML extends Component {
    async handleButtonsClicks(ev) {
        if (ev.target.tagName === "BUTTON" && ev.target.attributes && ev.target.attributes.type.value === "object") {
            const method_name = ev.target.attributes.name.value;
            const method_params = ev.target.attributes.method_args ? `,${JSON.parse(ev.target.attributes.method_args.value).join()}` : "";
            await this.env.model.root.update({todo_command: `button_clicked,${method_name}${method_params}`});
            this.env.kanbanDoAction(this.env.model.root.data.next_action_todo);
        }
    }
}
BankRecWidgetHTML.template = "account_accountant.BankRecWidgetHTML";

registry.category("fields").add("bank_rec_html", BankRecWidgetHTML);
