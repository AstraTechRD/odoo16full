/** @odoo-module alias=timesheet_grid.TimesheetM2OProject **/
import TimesheetM2OWidget from 'timesheet_grid.TimesheetM2OWidget';
import { _t } from 'web.core';
import { sprintf } from "@web/core/utils/strings";


const TimesheetM2OProject = TimesheetM2OWidget.extend({
    /**
     * @constructor
     */
    init: function (parent, value, rowIndex, workingHoursData) {
        this.modelName = 'project.project';
        this.fieldName = 'project_id';

        this._super.apply(this, arguments);
        this.title = sprintf(_t(
            'Difference between the number of %s allocated to the project and the number of %s recorded.'),
            this.cacheUnit, this.cacheUnit
        );
    },
});

export default TimesheetM2OProject;
