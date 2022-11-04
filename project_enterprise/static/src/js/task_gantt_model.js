/** @odoo-module **/

import { device } from 'web.config';
import { format } from 'web.field_utils';
import GanttModel from 'web_gantt.GanttModel';
import { _t } from 'web.core';


export default GanttModel.extend({
    mapMany2manyFields: [{
        many2many_field: 'personal_stage_type_ids',
        many2one_field: 'personal_stage_type_id',
    }],

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _fetchData() {
        const proms = [];
        proms.push(this._super(...arguments));
        proms.push(this._fetchMilestoneData());
        return Promise.all(proms);
    },
    /**
     * Retrieve the milestone data based on the task domain.
     *
     * @private
     */
    _fetchMilestoneData() {
        this.ganttData.milestones = [];
        if (this.isSampleModel || device.isMobile) {
            return Promise.resolve();
        }
        return this._rpc({
            model: 'project.milestone',
            method: 'search_milestone_from_task',
            kwargs: {
                task_domain: this.domain,
                milestone_domain: [
                    ['deadline', '<=', this.convertToServerTime(this.ganttData.stopDate)],
                    ['deadline', '>=', this.convertToServerTime(this.ganttData.startDate)],
                ],
                fields: ['name', 'deadline', 'is_deadline_exceeded', 'is_reached', 'project_id'],
                order: 'project_id ASC, deadline ASC',
            },
        }).then((milestones) => {
            this.ganttData.milestones = milestones.map(milestone => {
                return Object.assign(
                    milestone,
                    {
                        'deadlineUserFormatted': format.date(moment(milestone.deadline)),
                        // Ensure milestones are displayed at the end of the period.
                        'deadline': moment(milestone.deadline).clone().add(1, 'd').subtract(1, 'ms'),
                    },
                );
            });
        });
    },
    /**
     * @private
     * @override
     */
    _generateRows(params) {
        const { groupedBy, groups, parentPath } = params;
        if (groupedBy.length) {
            const groupedByField = groupedBy[0];
            if (groupedByField === 'user_ids') {
                // Here we are generating some rows under a common "parent" (if any).
                // We make sure that a row with resId = false for "user_id"
                // ('Unassigned Tasks') and same "parent" will be added by adding
                // a suitable fake group to groups (a subset of the groups returned
                // by read_group).
                const fakeGroup = Object.assign({}, ...parentPath);
                groups.push(fakeGroup);
            }
        }
        const rows = this._super(params);

        // Sort rows alphabetically, except when grouping by stage or personal stage
        if (!['stage_id', 'personal_stage_type_ids'].includes(rows[0].groupedByField)) {
            rows.sort((a, b) => {
                if (a.resId && !b.resId) return 1;
                if (!a.resId && b.resId) return -1;
                return a.name.toLowerCase() > b.name.toLowerCase() ? 1 : -1;
            });
        } else {
            // When not sorting, move empty rows to the top
            if (groupedBy && groupedBy.length && rows.length > 1 && rows[0].resId) {
                this._reorderEmptyRow(rows);
            }
        }
        return rows;
    },
    /**
     * @private
     * @override
     */
    _getRowName(groupedByField, value) {
        if (groupedByField === "user_ids") {
            const resId = Array.isArray(value) ? value[0] : value;
            if (!resId) {
                return _t("Unassigned Tasks");
            }
        }
        return this._super(...arguments);
    },
    /**
     * Find an empty row and move it at the head of the array.
     *
     * @private
     * @param {Object[]} rows
     */
    _reorderEmptyRow(rows) {
        let emptyIndex = null;
        for (let i = 0; i < rows.length; ++i) {
            if (!rows[i].resId) {
                emptyIndex = i;
                break;
            }
        }
        if (emptyIndex) {
            const emptyRow = rows.splice(emptyIndex, 1)[0];
            rows.unshift(emptyRow);
        }
    },
    /**
     * In the case of special Many2many Fields, like personal_stage_type_ids in project.task
     * model, we don't want to write the many2many field but use the inverse method of the
     * linked Many2one field, in this case the personal_stage_type_id, to create or update the
     * record - here set the stage_id - in the personal_stage_type_ids.
     *
     * See @project/src/js/task_gantt_controller::_getDialogContext() for
     * further explanation.
     *
     * @private
     * @override
     */
    rescheduleData: function (schedule, isUTC) {
        const data = this._super.apply(this, arguments);
        for (let mapping of this.mapMany2manyFields) {
            if (mapping.many2many_field in data) {
                data[mapping.many2one_field] = data[mapping.many2many_field][0];
                delete data[mapping.many2many_field];
            }
        }
        return data;
    },

    /**
     * @override
     */
    reschedule(ids, schedule, isUTC, callback) {
        if (!schedule.smart_task_scheduling) {
            return this._super(...arguments);
        }

        if (!(ids instanceof Array)) {
            ids = [ids];
        }

        const data = this.rescheduleData(schedule, isUTC);
        const end_date = moment(data.planned_date_end).endOf(this.get().scale);
        if (data.hasOwnProperty('name')){
            delete data.name;
        }
        return this.mutex.exec(() => {
            return this._rpc({
                model: this.modelName,
                method: 'schedule_tasks',
                args: [ids, data],
                context: Object.assign({}, this.context, {'last_date_view': this.convertToServerTime(end_date)}),
            }).then((result) => {
                if (callback) {
                    callback(result);
                }
            });
        });
    },
});
