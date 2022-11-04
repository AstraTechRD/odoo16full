odoo.define('timesheet_grid.TimerHeaderM2O', function (require) {
"use strict";

const config = require('web.config');
const core = require('web.core');
const relational_fields = require('web.relational_fields');
const StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
const Widget = require('web.Widget');
const session = require('web.session');

const Many2One = relational_fields.FieldMany2One;
const TaskWithHours = require('hr_timesheet.task_with_hours');
const _t = core._t;

const TimerHeaderM2O = Widget.extend(StandaloneFieldManagerMixin, {
    template: 'timesheet_grid.timer_project_task',
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} params
     */
    init: function (parent, params) {
        this._super(...arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.projectId = arguments[1];
        this.taskId = arguments[2];
    },
    /**
     * @private
     * @param {number} projectId
     * @return {Object} taskDomain
     */
     _getTaskDomain(projectId) {
        const taskDomain = [['allow_timesheets', '=', true]];
        if (projectId) {
            taskDomain.push(['project_id', '=', projectId]);
        }
        return taskDomain;
     },
    /**
     * @override
     */
    willStart: async function () {
        await this._super(...arguments);

        const projectDomain = [['allow_timesheets', '=', true]];
        if (session.user_companies) {
            // As the TimerHeaderComponent (in which TimerHeaderM2O is injected) is not injected unless the current
            // company timesheet UOM is hours, we can assume that current_uom_id is always hours UOM. Thus,
            // the bellow domain ensures that we only get projects of companies that uses hours UOM as timesheet UOM.
            const currentUOMId = session.user_companies.allowed_companies[session.company_id].timesheet_uom_id;
            projectDomain.push(['timesheet_encode_uom_id', '=', currentUOMId]);
        }

        this.project = await this.model.makeRecord('account.analytic.line', [{
            name: 'project_id',
            relation: 'project.project',
            type: 'many2one',
            value: this.projectId,
            domain: projectDomain,
        }]);

        this.task = await this.model.makeRecord('account.analytic.line', [{
            name: 'task_id',
            relation: 'project.task',
            type: 'many2one',
            value: this.taskId,
            domain: this._getTaskDomain(this.projectId),
        }]);
    },
    /**
     * @override
     */
    start: async function () {
        const _super = this._super.bind(this);
        let placeholderTask, placeholderProject;
        if (config.device.isMobile) {
            placeholderTask = _t('Task');
            placeholderProject = _t('Project');
        } else {
            placeholderTask = _t('Select a Task');
            placeholderProject = _t('Select a Project');
        }
        const projectRecord = this.model.get(this.project);
        const projectMany2one = new Many2One(this, 'project_id', projectRecord, {
            attrs: {
                placeholder: placeholderProject,
                options: { no_create_edit: true },
            },
            noOpen: true,
            mode: 'edit',
            required: true,
        });
        projectMany2one.field['required'] = true;
        this._registerWidget(this.project, 'project_id', projectMany2one);
        projectMany2one.renderElement();
        const timerProjectId = this.el.querySelector('.timer_project_id');
        await projectMany2one.appendTo(timerProjectId);
        this.projectMany2one = projectMany2one;
        projectMany2one.el.classList.add('w-100');

        const taskRecord = this.model.get(this.task);
        const taskMany2one = new TaskWithHours(this, 'task_id', taskRecord, {
            attrs: {
                placeholder: placeholderTask,
                options: { no_create_edit: true },
            },
            noOpen: true,
            mode: 'edit',
        });
        taskMany2one.field['context'] = this.projectId ? { 'default_project_id': this.projectId } : {};
        this._registerWidget(this.task, 'task_id', taskMany2one);
        taskMany2one.renderElement();
        const timerTaskId = this.el.querySelector('.timer_task_id');
        await taskMany2one.appendTo(timerTaskId);
        this.taskMany2one = taskMany2one;
        timerTaskId.classList.add('o_required_modifier');
        taskMany2one.el.classList.add('w-100');

        _super.apply(...arguments);
    },
    /**
     * @private
     */
    _updateRequiredField: function () {
        if (this.projectId === undefined) {
            this.$('.timer_label_project').addClass('o_field_invalid');
            this.$('.timer_project_id').addClass('o_field_invalid');
        } else {
            this.$('.timer_label_project').removeClass('o_field_invalid');
            this.$('.timer_project_id').removeClass('o_field_invalid');
        }
    },

    /**
     * @private
     * @override
     * @param {OdooEvent} ev
     */
    _onFieldChanged: async function (ev) {
        const project = this.projectId;
        const task = (this.taskId) ? this.taskId : false;
        await StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
        const fieldName = ev.target.name;
        let record;
        if (fieldName === 'project_id') {
            record = this.model.get(this.project);
            var newId = record.data.project_id.res_id;
            if (project !== newId) {
                this.projectId = newId;
                this.taskId = false;
                this.taskMany2one._render();
                this.taskMany2one.field.domain = this._getTaskDomain(newId);
                this.taskMany2one.field.context = newId ? {'default_project_id': newId} : {};
                this.trigger_up('timer-edit-project', {'projectId': newId});
                this._updateRequiredField();
            }
        } else if (fieldName === 'task_id') {
            record = this.model.get(this.task);
            const newId = record.data.task_id && record.data.task_id.res_id;
            if (task !== newId) {
                let project_id = this.projectId;
                if (!project_id) {
                    const task_data = await this._rpc({
                        model: 'project.task',
                        method: 'search_read',
                        args: [[['id', '=', newId]], ['project_id']],
                    });
                    project_id = task_data[0].project_id[0];
                }

                this.taskId = false;
                this.trigger_up('timer-edit-task', {'taskId': newId, 'projectId': project_id});
            }
        }
    },
});

return TimerHeaderM2O;

});
