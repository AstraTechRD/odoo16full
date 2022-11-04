odoo.define('forecast.ForecastGanttView', function (require) {
    'use strict';

    var PlanningGanttModel = require('planning.PlanningGanttModel');
    var PlanningGanttView = require('planning.PlanningGanttView');
    var view_registry = require('web.view_registry');

    var ForecastGanttModel = PlanningGanttModel.extend({
        /**
         * @override
         */
        reload: function (handle, params) {
            if ('context' in params && params.context.planning_groupby_project && !params.groupBy.length) {
                params.groupBy.unshift('project_id');
            }

            return this._super(handle, params);
        }
    });

    var ForecastGanttView = PlanningGanttView.extend({
        config: _.extend({}, PlanningGanttView.prototype.config, {
            Model: ForecastGanttModel,
        }),
    });

    view_registry.add('forecast_gantt', ForecastGanttView);

    return ForecastGanttView;

});
