/** @odoo-module */

import { KanbanRecord } from '@web/views/kanban/kanban_record';

export class FsmProductKanbanRecord extends KanbanRecord {
    onGlobalClick(ev) {
        if (ev.target.closest('.o_fsm_product_quantity')) {
            return;
        }
        return super.onGlobalClick(ev);
    }
}
