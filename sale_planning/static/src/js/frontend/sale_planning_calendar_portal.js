/** @odoo-module **/

import PlanningView from 'planning.calendar_frontend';

PlanningView.include({
    // override popup of calendar
    eventFunction: function (calEvent) {
        this._super.apply(this, arguments);
        const $saleLine = $("#sale_line");
        if (calEvent.event.extendedProps.sale_line) {
            $saleLine.text(calEvent.event.extendedProps.sale_line);
            $saleLine.css("display", "");
            $saleLine.prev().css("display", "");
        } else {
            $saleLine.css("display", "none");
            $saleLine.prev().css("display", "none");
        }
    },
});
