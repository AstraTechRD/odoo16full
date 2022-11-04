odoo.define('planning.PlanningGanttView', function (require) {
    'use strict';

    const HrGanttView = require('hr_gantt.GanttView');
    const PlanningGanttController = require('planning.PlanningGanttController');
    const PlanningGanttModel = require('planning.PlanningGanttModel');
    const PlanningGanttRenderer = require('planning.PlanningGanttRenderer');

    const view_registry = require('web.view_registry');

    const PlanningGanttView = HrGanttView.extend({
        config: Object.assign({}, HrGanttView.prototype.config, {
            Renderer: PlanningGanttRenderer,
            Controller: PlanningGanttController,
            Model: PlanningGanttModel,
        }),

        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
            // take parameters from url if set https://example.com/web?date_start=2020-11-08&scale=week
            // this is used by the mail of planning.planning
            const url = new URLSearchParams(window.location.search);
            if (url.get('date_start')) {
                this.loadParams.initialDate = moment(url.get('date_start'));

                if(url.get('date_end')) {
                    const start = this.loadParams.initialDate;
                    const end = moment(url.get('date_end'));

                    if (start.isSame(end, 'week')) {
                        this.loadParams.scale = 'week';
                    } else {
                        this.loadParams.scale = 'month';
                    }
                }
            }
        }
    });

    view_registry.add('planning_gantt', PlanningGanttView);

    return PlanningGanttView;
});
