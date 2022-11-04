/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useSignViewButtons } from "@sign/views/hooks";

export class SignKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        const functions = useSignViewButtons();
        Object.assign(this, functions);
    }
}
