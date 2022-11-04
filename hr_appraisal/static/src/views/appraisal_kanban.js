/** @odoo-module */

import { registry } from '@web/core/registry';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { EmployeeKanbanModel } from '@hr/views/kanban_view';

registry.category('views').add('appraisal_kanban', {
    ...kanbanView,
    Model: EmployeeKanbanModel,
});
