odoo.define('planning.PlanningGanttRenderer', function (require) {
    'use strict';

    const HrGanttRenderer = require('hr_gantt.GanttRenderer');
    const PlanningGanttRow = require('planning.PlanningGanttRow');

    const PlanningGanttRenderer = HrGanttRenderer.extend({
        config: Object.assign({}, HrGanttRenderer.prototype.config, {
            GanttRow: PlanningGanttRow
        }),

        sampleDataTargets: [
            '.o_gantt_row[data-from-server=true]',
        ],
        async _renderView() {
            await this._super(...arguments);
            this.el.classList.add('o_planning_gantt');
        },

        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$el.addClass('o_planning_gantt');
            });
        },
    });

    return PlanningGanttRenderer;
});
