/** @odoo-module **/

import { PlanningCalendarController } from "@planning/views/planning_calendar/planning_calendar_controller";
import { patch } from "@web/core/utils/patch";
import { useSalePlanningViewHook } from "@sale_planning/views/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";

patch(PlanningCalendarController.prototype, "sale_planning_calendar_controller", {
    setup() {
        this._super(...arguments);
        const functions = useSalePlanningViewHook({
            getDomain: () => this.model.computeDomain(this.model.data),
            getViewContext: () => (Object.assign({}, this.props.context, {
                scale: this.model.scale,
                focus_date: serializeDateTime(this.model.meta.date),
                start_date: serializeDateTime(this.model.rangeStart),
                stop_date: serializeDateTime(this.model.rangeEnd),
            })),
            getScale: () => this.model.scale,
            getFocusDate: () => this.model.meta.date,
        });
        Object.assign(this, functions);
    },
});
