/** @odoo-module */

import { registry } from "@web/core/registry";
import { FloatFactorField } from "@web/views/fields/float_factor/float_factor_field";
import { FloatToggleField } from "@web/views/fields/float_toggle/float_toggle_field";

import { TimesheetUOM } from "@hr_timesheet/components/timesheet_uom/timesheet_uom";
import { TimesheetUOMHourTimer } from "../timesheet_uom_hour_timer/timesheet_uom_hour_timer";


class TimesheetUOMTimer extends TimesheetUOM {

    get timesheetWidget() {
        const timesheet_widget = super.timesheetWidget;
        return timesheet_widget === "float_time" ? "timesheet_uom_hour_timer" : timesheet_widget;
    }

}

TimesheetUOMTimer.components = {
    ...TimesheetUOM.components,
    FloatFactorField, FloatToggleField, TimesheetUOMHourTimer
};

// As we replace FloatTimeField by TimesheetUOMHourTimer, we remove it from the components that we get from TimesheetUOM.
delete TimesheetUOMTimer.components.FloatTimeField;

registry.category("fields").add("timesheet_uom_timer", TimesheetUOMTimer);
