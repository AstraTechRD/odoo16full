/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class AccountsListController extends ListController {
    setup() {
        super.setup()
    }

    _importAccountAction() {
        this.actionService.doAction("account_base_import.action_open_import_guide");
    }
};

const AccountsListView = {
    ...listView,
    Controller: AccountsListController,
    buttonTemplate: "account_base_import.AccountListView.buttons",
};

registry.category("views").add("accountchart_tree_import", AccountsListView);
