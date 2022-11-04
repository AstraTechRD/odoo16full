/** @odoo-module */

import { kanbanView } from "@web/views/kanban/kanban_view";
import { MrpWorkorderKanbanController } from "./mrp_workorder_kanban_controller";
import { registry } from "@web/core/registry";

export const MrpWorkorderKanbanView = {
    ...kanbanView,
    Controller: MrpWorkorderKanbanController,
    buttonTemplate: 'mrp_workorder.overviewButtonsKanban',
};

registry.category("views").add('tablet_kanban_view', MrpWorkorderKanbanView);
