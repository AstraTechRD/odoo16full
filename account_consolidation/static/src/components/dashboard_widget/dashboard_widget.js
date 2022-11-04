/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class ConsolidationDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get datas() {
        return JSON.parse(this.props.value);
    }


    async onUnmappedAccountClick(company_id) {
        const action = await this.orm.call('consolidation.period', 'action_open_mapping', 
            [this.props.record.resId], {context: {company_id: company_id}});
        this.action.doAction(action);
    }    
}
ConsolidationDashboard.template = "account_consolidation.ConsolidatedDashboardTemplate";
ConsolidationDashboard.supportedTypes = ["char"];

registry.category("fields").add("consolidation_dashboard_field", ConsolidationDashboard);
