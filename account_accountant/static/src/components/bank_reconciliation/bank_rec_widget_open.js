/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class OpenBankRecWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async openBankRec(ev) {
        const action = await this.orm.call("account.bank.statement", "action_open_bank_reconcile_widget", [this.props.record.resId], {});
        this.action.doAction(action);
    }
}

OpenBankRecWidget.template = "account.OpenBankRecWidget";
registry.category("fields").add("bank_rec_widget_open", OpenBankRecWidget);
