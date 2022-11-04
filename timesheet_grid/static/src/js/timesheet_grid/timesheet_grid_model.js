odoo.define('timesheet_grid.GridModel', function (require) {
    "use strict";

    const CommonTimesheetGridModel = require('timesheet_grid.CommonTimesheetGridModel');

    const TimesheetGridModel = CommonTimesheetGridModel.extend({

        /**
         * @private
         * @override
         */
        _fetch(groupBy) {
            if (!this.currentRange) {
                return Promise.resolve();
            }

            if (this.sectionField && groupBy.length > 1 && this.sectionField === groupBy[0]) {
                return this._fetchGroupedData(groupBy);
            } else {
                return this._fetchUngroupedData(groupBy);
            }
        },

        /**
         * @override
         */
        async __load(params) {
            const result = await this._super(...arguments);

            this._gridData.timeBoundariesContext = this._getTimeContext();
            this._gridData.workingHoursData = await this.fetchAllTimesheetM2OAvatarData(this._getGridValues('employee_id'), this._gridData.timeBoundariesContext.start, this._gridData.timeBoundariesContext.end);

            return result;
        },

        /**
         * @override
         */
        async __reload(handle, params) {
            const result = await this._super(...arguments);

            this._gridData.timeBoundariesContext = this._getTimeContext();
            this._gridData.workingHoursData = await this.fetchAllTimesheetM2OAvatarData(this._getGridValues('employee_id'), this._gridData.timeBoundariesContext.start, this._gridData.timeBoundariesContext.end);

            return result;
        },

        /**
         * Perform a rpc to get the data for the timesheet avatar widget.
         *
         * @param employeesGridData employees data gathered from the grid.
         * @param {String} start the range start data
         * @param {String} end the range end date
         * @returns {Promise<object|*>}
         */
        async fetchAllTimesheetM2OAvatarData(employeesGridData, start, end) {

            // If there is no data, we don't bother
            if (employeesGridData.length === 0) {
                return {};
            }

            const hoursData = await this._rpc({
                model: 'hr.employee',
                method: 'get_timesheet_and_working_hours_for_employees',
                args: [employeesGridData, start, end],
            });

            return hoursData;
        },

    });

    return TimesheetGridModel;
});
