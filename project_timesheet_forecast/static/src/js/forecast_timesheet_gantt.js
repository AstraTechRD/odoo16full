odoo.define('forecast_timesheet.ForecastTimesheetGanttView', function (require) {
    'use strict';

    const viewRegistry = require('web.view_registry');
    const ForecastGanttView = require('forecast.ForecastGanttView');
    const PlanningGanttRenderer = require('planning.PlanningGanttRenderer');
    const PlanningGanttRow = require('planning.PlanningGanttRow');
    const fieldUtils = require('web.field_utils');

    const ForecastTimesheetGanttRow = PlanningGanttRow.extend({

        /**
         * Add effective hours formatted to context
         *
         * @private
         * @override
         */
        _getPopoverContext() {
            const data = this._super(...arguments);
            data.effectiveHoursFormatted = fieldUtils.format.float_time(data.effective_hours);
            data.effectivePercentageFormatted = fieldUtils.format.float(data.percentage_hours);
            return data;
        },
    });

    const ForecastTimesheetGanttRenderer = PlanningGanttRenderer.extend({
        config: Object.assign({}, PlanningGanttRenderer.prototype.config, {
            GanttRow: ForecastTimesheetGanttRow,
        }),
    });

    const ForecastTimesheetGanttView = ForecastGanttView.extend({
        config: Object.assign({}, ForecastGanttView.prototype.config, {
            Renderer: ForecastTimesheetGanttRenderer,
        }),
    });

    viewRegistry.add('forecast_timesheet', ForecastTimesheetGanttView);
    return ForecastTimesheetGanttView;
});
