/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class OnlineSyncListController extends ListController {
    createBankAccountAction() {
        this.actionService.doAction("account.action_new_bank_setting");
    }
}

const OnlineSyncListView = {
    ...listView,
    Controller: OnlineSyncListController,
    buttonTemplate: "account_online_synchronization.ListView.buttons",
};

registry.category("views").add("online_sync_tree", OnlineSyncListView);
