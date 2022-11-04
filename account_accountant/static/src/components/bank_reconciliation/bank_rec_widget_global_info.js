/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

export class BankRecWidgetGlobalInfo extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        onWillStart(() => this.fetchData(this.props));
    }

    async fetchData(props) {
        if (props.journal_id) {
            this.data = await this.orm.call("bank.rec.widget",
                "collect_global_info_data",
                ['', props.journal_id],
                {}
            );
        }
    }

    async openReport() {
        const actionData = await this.orm.call(
            "bank.rec.widget",
            "action_open_bank_reconciliation_report",
            ['', this.props.journal_id],
            {}
        );
        this.action.doAction(actionData);
    }

}
BankRecWidgetGlobalInfo.template = "account_accountant.BankRecWidgetGlobalInfo";

registry.category("fields").add("bank_rec_widget_global_info", BankRecWidgetGlobalInfo);
