/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";

export class MrpWorkorderListController extends ListController {
    actionBack() {
        this.actionService.doAction("mrp.mrp_workcenter_kanban_action", {
            clearBreadcrumbs: true,
        });
    }
}
