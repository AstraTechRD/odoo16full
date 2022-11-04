/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class MatchingLink extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async reconcile() {
        const action = await this.orm.call("account.move.line", "action_reconcile", [this.props.record.resId], {});
        this.action.doAction(action);
    }

    async viewMatch() {
        const action = await this.orm.call("account.move.line", "open_reconcile_view", [this.props.record.resId], {});
        this.action.doAction(action, { additionalContext: { is_matched_view: true }});
    }
}

MatchingLink.template = "account_accountant.MatchingLink";
registry.category("fields").add("matching_link_widget", MatchingLink);
