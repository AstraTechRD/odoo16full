/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { TimerToggleButton } from "@timer/component/timer_toggle_button/timer_toggle_button";
import { TimesheetDisplayTimer } from "../timesheet_display_timer/timesheet_display_timer";


const { Component, useState } = owl;

export class FieldTimesheetHourToggle extends Component {

    setup() {
        super.setup();
        this.ormService = useService("orm");
        this.state = useState({
            displayButton: false,
        });
    }

    async _performActionAndReload(action) {
        await this.ormService.call(this.props.record.resModel, action, [[this.props.record.resId]]);
        await this.props.record.load();
        this.props.record.model.notify();
    }

    async onClickDecrease() {
        await this._performActionAndReload("action_timer_decrease");
    }

    async onClickIncrease() {
        await this._performActionAndReload("action_timer_increase");
    }

    async onMouseOver() {
        this.state.displayButton = true;
    }

    async onMouseOut() {
        this.state.displayButton = false;
    }

    get TimesheetDisplayTimerProps() {
        return { ...this.props, value: this.props.record.data.duration_unit_amount };
    }

    get TimerToggleButtonProps() {
        return { ...this.props, value: this.props.record.data.is_timer_running };
    }

}

FieldTimesheetHourToggle.template = "timesheet_grid.TimesheetUOMHoursToggle";

FieldTimesheetHourToggle.components = { TimesheetDisplayTimer, TimerToggleButton };

FieldTimesheetHourToggle.fieldDependencies = {
    duration_unit_amount: { type: "float" },
    is_timer_running: { type: "boolean" },
};

FieldTimesheetHourToggle.props = {
    ...standardFieldProps,
};

registry.category("fields").add("timesheet_uom_hour_toggle", FieldTimesheetHourToggle);
