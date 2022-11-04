/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { FsmProductKanbanModel } from "./fsm_product_kanban_model";
import { FsmProductKanbanRenderer } from "./fsm_product_kanban_renderer";

export const fsmProductKanbanView = {
    ...kanbanView,
    Model: FsmProductKanbanModel,
    Renderer: FsmProductKanbanRenderer,
};

registry.category('views').add('fsm_product_kanban', fsmProductKanbanView);
