/** @odoo-module */
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";

async function executeSubscriptionDashboardDownload({ env, action, options }) {
    env.services.ui.block();
    const url = "/salesman_subscription_reports";
    const data = action.data;
    try {
        await download({ url, data });
    } finally {
        env.services.ui.unblock();
    }
}

registry
    .category("action_handlers")
    .add("ir_actions_sale_subscription_dashboard_download", executeSubscriptionDashboardDownload);
