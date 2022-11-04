/** @odoo-module */

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { FsmProductKanbanRecord } from "./fsm_product_kanban_record";

export class FsmProductKanbanRenderer extends KanbanRenderer { }

FsmProductKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanRecord: FsmProductKanbanRecord,
};
