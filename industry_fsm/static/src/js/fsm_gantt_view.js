/** @odoo-module **/

import viewRegistry from 'web.view_registry';
import TaskGanttView from '@project_enterprise/js/task_gantt_view';
import FsmGanttController from './fsm_gantt_controller';

export const FsmGanttView = TaskGanttView.extend({
    config: Object.assign({}, TaskGanttView.prototype.config, {
        Controller: FsmGanttController,
    }),
});

viewRegistry.add('task_gantt', FsmGanttView);
