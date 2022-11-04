/** @odoo-module **/

import { CalendarController } from "@web/views/calendar/calendar_controller";
import { useService } from "@web/core/utils/hooks";
import { usePlanningViewHook } from "@planning/views/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";

const { onWillStart } = owl;

export class PlanningCalendarController extends CalendarController {
    setup() {
        super.setup(...arguments);
        this.user = useService("user");

        onWillStart(this.onWillStart);

        const getDomain = () => this.model.computeDomain(this.model.data);
        const functions = usePlanningViewHook({
            getDomain,
            getStartDate: () => this.model.rangeStart,
            getRecords: () => Object.values(this.model.records),
            getAdditionalContext: () => ({
                default_start_datetime: serializeDateTime(this.model.rangeStart),
                default_end_datetime: serializeDateTime(this.model.rangeEnd),
                default_slot_ids: Object.values(this.model.records).map(rec => rec.id),
                scale: this.model.scale,
                active_domain: getDomain(),
            }),
        });
        Object.assign(this, functions);
    }

    async onWillStart() {
        this.isManager = await this.user.hasGroup("planning.group_planning_manager");
    }
};
PlanningCalendarController.template = "planning.PlanningCalendarController";
