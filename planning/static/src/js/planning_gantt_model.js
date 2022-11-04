/** @odoo-module alias=planning.PlanningGanttModel **/

import GanttModel from 'web_gantt.GanttModel';
import { _t } from 'web.core';
import { formatPercentage } from "@web/views/fields/formatters";

const GROUPBY_COMBINATIONS = [
    "role_id",
    "role_id,resource_id",
    "role_id,department_id",
    "department_id",
    "department_id,role_id",
    "project_id",
    "project_id,department_id",
    "project_id,resource_id",
    "project_id,role_id",
    "project_id,task_id,resource_id",
    "project_id,task_id,role_id",
    "task_id",
    "task_id,department_id",
    "task_id,resource_id",
    "task_id,role_id",
];

const PlanningGanttModel = GanttModel.extend({

    /**
     * @public
     * @returns {moment} startDate
     */
    getStartDate() {
        return this.convertToServerTime(this.get().startDate);
    },
    /**
     * @public
     * @param {Object} ctx
     * @returns {Object} context
     */
    getAdditionalContext(ctx) {
        const state = this.get();
        return Object.assign({}, ctx, {
            'default_start_datetime': this.convertToServerTime(state.startDate),
            'default_end_datetime': this.convertToServerTime(state.stopDate),
            'default_slot_ids': state.records.map(record => record.id),
            'scale': state.scale,
            'active_domain': this.domain,
            'active_ids': state.records,
            'default_employee_ids': state.rows.map(row => row.resId).filter(resId => !!resId),
        });
    },
    /**
     * @override
     */
    _fetchData: function () {
        this.context.show_job_title = true;
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    __reload(handle, params) {
        if ("context" in params) {
            params.context.show_job_title = true;
            if (params.context.planning_groupby_role && !params.groupBy.length) {
                params.groupBy.unshift('resource_id');
                params.groupBy.unshift('role_id');
            }
        }
        return this._super(handle, params);
    },
    /**
     * Check if the given groupedBy includes fields for which an empty fake group will be created
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowCreateEmptyGroups(groupedBy) {
        return groupedBy.includes("resource_id");
    },
    /**
     * Check if the given groupBy is in the list that has to generate empty lines
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowedEmptyGroups(groupedBy) {
        return GROUPBY_COMBINATIONS.includes(groupedBy.join(","));
    },
    /**
     * @private
     * @override
     * @returns {Object[]}
     */
    _generateRows(params) {
        const { groupedBy, groups, parentPath } = params;
        if (!this.hide_open_shift) {
            if (parentPath.length === 0) {
                // _generateRows is a recursive function.
                // Here, we are generating top level rows.
                if (this._allowCreateEmptyGroups(groupedBy)) {
                    // The group with false values for every groupby can be absent from
                    // groups (= groups returned by read_group basically).
                    // Here we add the fake group {} in groups in any case (this simulates the group
                    // with false values mentionned above).
                    // This will force the creation of some rows with resId = false
                    // (e.g. 'Open Shifts') from top level to bottom level.
                    groups.push({});
                }
                if (this._allowedEmptyGroups(groupedBy)) {
                    params.addOpenShifts = true;
                }
            }
            if (params.addOpenShifts && groupedBy.length === 1) {
                // Here we are generating some rows on last level (assuming
                // collapseFirstLevel is false) under a common "parent"
                // (if any: first level can be last level).
                // We make sure that a row with resId = false for
                // the unique groupby in groupedBy and same "parent" will be
                // added by adding a suitable fake group to the groups (a subset
                // of the groups returned by read_group).
                const fakeGroup = Object.assign({}, ...parentPath);
                groups.push(fakeGroup);
            }
        }
        const rows = this._super(params);
        // always move an empty row to the head and sort rows alphabetically
        if (groupedBy && groupedBy.length && rows.length > 1 && rows[0].resId) {
            rows.sort((curr, next) => {
                if (curr.resId && !next.resId) return 1;
                if (!curr.resId && next.resId) return -1;
                return curr.name.toLowerCase() > next.name.toLowerCase() ? 1 : -1;
            });
            this._reorderEmptyRow(rows);
        }
        return rows;
    },
    /**
     * Rename 'Undefined Resource' and 'Undefined Department' to 'Open Shifts'.
     *
     * @private
     * @override
     */
    _getRowName(groupedByField, value) {
        if (["department_id", "resource_id"].includes(groupedByField)) {
            const resId = Array.isArray(value) ? value[0] : value;
            if (!resId) {
                return _t("Open Shifts");
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
     * Recursive function to add progressBar info to rows grouped by the field.
     *
     * @private
     * @override
     */
    _addProgressBarInfo(field, rows, progressBarInfo) {
        this._super(...arguments);
        const rowsWithProgressBar = rows.filter((row) => row.progressBar && row.progressBar.max_value_formatted);
        for (const row of rowsWithProgressBar) {
            row.progressBar.percentage = formatPercentage(row.progressBar.ratio / 100);
        }
    },
});

export default PlanningGanttModel;
