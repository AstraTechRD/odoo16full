/** @odoo-module */

import { listView } from "@web/views/list/list_view";
import { MrpWorkorderListController } from "./mrp_workorder_list_controller";
import { registry } from "@web/core/registry";

export const MrpWorkorderListView = {
    ...listView,
    Controller: MrpWorkorderListController,
    buttonTemplate: "mrp_workorder.overviewButtonsList",
};

registry.category("views").add("tablet_list_view", MrpWorkorderListView);
