odoo.define('hr_gantt.GanttView', function (require) {
    'use strict';

    const viewRegistry = require('web.view_registry');
    const GanttView = require('web_gantt.GanttView');
    const HrGanttRenderer = require('hr_gantt.GanttRenderer');

    const HrGanttView = GanttView.extend({
        config: Object.assign({}, GanttView.prototype.config, {
            Renderer: HrGanttRenderer,
        }),
    });

    viewRegistry.add('hr_gantt', HrGanttView);
    return HrGanttView;
});
