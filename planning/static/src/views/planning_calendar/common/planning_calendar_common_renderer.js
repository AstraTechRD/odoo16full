/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { PlanningCalendarCommonPopover } from "@planning/views/planning_calendar/common/planning_calendar_common_popover";

export class PlanningCalendarCommonRenderer extends CalendarCommonRenderer {}
PlanningCalendarCommonRenderer.components = {
    ...CalendarCommonRenderer.components,
    Popover: PlanningCalendarCommonPopover,
};
