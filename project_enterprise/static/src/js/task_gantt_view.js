/** @odoo-module **/

import viewRegistry from 'web.view_registry';
import GanttView from 'web_gantt.GanttView';
import TaskGanttController from './task_gantt_controller';
import TaskGanttRenderer from './task_gantt_renderer';
import TaskGanttModel from './task_gantt_model';
import { ProjectControlPanel } from '@project/js/project_control_panel';

const TaskGanttView = GanttView.extend({
    config: Object.assign({}, GanttView.prototype.config, {
        Controller: TaskGanttController,
        Renderer: TaskGanttRenderer,
        Model: TaskGanttModel,
        ControlPanel: ProjectControlPanel,
    }),

    //--------------------------------------------------------------------------
    // Life Cycle
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super(...arguments);
        const fieldsToFetch = ['project_id']
        if (this.rendererParams.dependencyEnabled) {
            fieldsToFetch.push('allow_task_dependencies', 'display_warning_dependency_in_gantt');
        }
        this.loadParams.decorationFields.push(...fieldsToFetch);
    }
});

viewRegistry.add('task_gantt', TaskGanttView);

export default TaskGanttView;
