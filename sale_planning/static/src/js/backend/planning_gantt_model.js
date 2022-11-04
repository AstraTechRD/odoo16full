/** @odoo-module **/

import PlanningGanttModel from '@planning/js/planning_gantt_model';

const GROUPBY_COMBINATIONS = [
    "sale_line_id",
    "sale_line_id,department_id",
    "sale_line_id,resource_id",
    "sale_line_id,role_id",
];

PlanningGanttModel.include({
    /**
     * @override
     */
    reload: function (handle, params) {
        if ('context' in params && params.context.planning_groupby_sale_order && !params.groupBy.length) {
            params.groupBy.unshift('sale_line_id');
        }

        return this._super(handle, params);
    },
    /**
     * Check if the given groupedBy includes fields for which an empty fake group will be created
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowCreateEmptyGroups(groupedBy) {
        return this._super(...arguments) || groupedBy.includes("sale_line_id");
    },
    /**
     * Check if the given groupBy is in the list that has to generate empty lines
     * @param {string[]} groupedBy
     * @returns {boolean}
     */
    _allowedEmptyGroups(groupedBy) {
        return this._super(...arguments) || GROUPBY_COMBINATIONS.includes(groupedBy.join(","));
    },
});
