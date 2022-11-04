/** @odoo-module */

import { patch } from 'web.utils';
import CommonTimesheetGridRenderer from 'timesheet_grid.CommonTimesheetGridRenderer';
import TimesheetGridRenderer from 'timesheet_grid.GridRenderer';
import TimerGridRenderer from 'timesheet_grid.TimerGridRenderer';
import TimesheetM2OSOLine from 'sale_timesheet_enterprise.TimesheetM2OSOLine';


patch(CommonTimesheetGridRenderer.prototype, 'sale_timesheet_enterprise.CommonTimesheetGridRenderer', {
    setup() {
        this._super();
        this.widgetComponents.TimesheetM2OSOLine = TimesheetM2OSOLine;
        this.widgetFieldNames = [...this.widgetFieldNames, 'so_line'];
    },
});

TimesheetGridRenderer.props.solHoursData = {
    type: Object,
    optional: true,
};

TimerGridRenderer.props.solHoursData = {
    type: Object,
    optional: true,
};
