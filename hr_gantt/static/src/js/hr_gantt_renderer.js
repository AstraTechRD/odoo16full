odoo.define('hr_gantt.GanttRenderer', function (require) {
    'use strict';

    const GanttRenderer = require('web_gantt.GanttRenderer');
    const HrGanttRow = require('hr_gantt.GanttRow');

    const HrGanttRenderer = GanttRenderer.extend({
        config: Object.assign({}, GanttRenderer.prototype.config, {
            GanttRow: HrGanttRow
        }),
    });

    return HrGanttRenderer;
});
