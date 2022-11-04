/** @odoo-module **/

import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { PlanningCalendarController } from "@planning/views/planning_calendar/planning_calendar_controller";
import { PlanningCalendarRenderer } from "@planning/views/planning_calendar/planning_calendar_renderer";

export const planningCalendarView = {
    ...calendarView,
    Controller: PlanningCalendarController,
    Renderer: PlanningCalendarRenderer,

    buttonTemplate: "planning.PlanningCalendarController.controlButtons",
};
registry.category("views").add("planning_calendar", planningCalendarView);
