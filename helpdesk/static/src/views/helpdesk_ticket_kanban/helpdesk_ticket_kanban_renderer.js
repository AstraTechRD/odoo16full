/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

export class HelpdeskTicketRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.action = useService('action');
    }

    async deleteGroup(group) {
        if (group && group.groupByField.name === 'stage_id') {
            const action = await group.model.orm.call(
                group.resModel,
                'action_unlink_wizard',
                [group.resId],
                { context: group.context },
            );
            this.action.doAction(action);
            return;
        }
        super.deleteGroup(group);
    }
}
