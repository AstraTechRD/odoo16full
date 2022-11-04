/** @odoo-module **/

import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';

export const iotBoxKanbanView = {
    ...kanbanView,
    buttonTemplate: 'iot.iot_box.KanbanView.Buttons',
};

registry.category('views').add('box_kanban_view', iotBoxKanbanView);
