/** @odoo-module alias=planning.PlanningGanttRow **/

import HrGanttRow from 'hr_gantt.GanttRow';
import EmployeeWithJobTitle from '@planning/js/widgets/employee_m2o_with_job_title';
import fieldUtils from 'web.field_utils';

const PlanningGanttRow = HrGanttRow.extend({
    template: 'PlanningGanttView.Row',

    init(parent, pillsInfo, viewInfo, options) {
        this._super(...arguments);
        const isGroupedByResource = pillsInfo.groupedByField === 'resource_id';
        const isEmptyGroup = pillsInfo.groupId === 'empty';
        this.employeeID = (this.progressBar && this.progressBar.employee_id) || false;
        this.isResourceMaterial = !!(this.progressBar && this.progressBar.is_material_resource);
        this.showEmployeeAvatar = !this.isResourceMaterial && (isGroupedByResource && !isEmptyGroup && !!this.employeeID);
    },

    _getEmployeeID() {
        return this.employeeID;
    },

    /**
     * Add allocated hours formatted to context
     *
     * @private
     * @override
     */
    _getPopoverContext: function () {
        const data = this._super.apply(this, arguments);
        data.allocatedHoursFormatted = fieldUtils.format.float_time(data.allocated_hours);
        data.allocatedPercentageFormatted = fieldUtils.format.float(data.allocated_percentage);
        return data;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initialize the avatar widget in virtual DOM.
     *
     * @private
     * @override
     * @returns {Promise}
     */
    async _preloadAvatarWidget() {
        const employee = [this._getEmployeeID(), this.name];
        this.avatarWidget = new EmployeeWithJobTitle(this, employee, this.planningHoursInfo);
        return this.avatarWidget.appendTo(document.createDocumentFragment());
    },

    /**
     * Return the total allocated hours
     *
     * @private
     * @override
     * @param {Object} pill
     * @returns {string}
     */
    _getAggregateGroupedPillsDisplayName(pill) {
        const totalAllocatedHours = pill.aggregatedPills.reduce((acc, val) => acc + val.allocated_hours, 0).toFixed(2);
        return fieldUtils.format.float_time(totalAllocatedHours);
    },

});

export default PlanningGanttRow;
