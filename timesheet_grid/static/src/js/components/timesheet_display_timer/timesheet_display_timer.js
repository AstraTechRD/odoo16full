/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@web/views/fields/formatters";
import { FloatTimeField } from "@web/views/fields/float_time/float_time_field";

const { Component, useState, onWillStart, onWillDestroy, onWillUpdateProps } = owl;


export class TimesheetTimerFloatTimerField extends FloatTimeField {

    get formattedValue() {
        return formatFloatTime(this.props.value, { displaySeconds: this.props.timerRunning });
    }

}

TimesheetTimerFloatTimerField.template = "timesheet_grid.TimesheetTimerFloatTimeField";
TimesheetTimerFloatTimerField.props = {
    ...FloatTimeField.props,
    timerRunning: { type: Boolean },
};

export class TimesheetDisplayTimer extends Component {

    setup() {
        this.timerService = useService("timer");
        this.state = useState({
            timerRunning: Boolean(this.props.record.data.timer_start) && !Boolean(this.props.record.data.timer_pause),
            value: this.props.value,
        });
        onWillStart(this.onWillStart);
        onWillUpdateProps(this.onWillUpdateProps);
        onWillDestroy(this._stopTimeRefresh);
    }

    async onWillUpdateProps(nextProps) {
        let newValue = nextProps.value;
        if (this.state.timerRunning) {
            this._stopTimeRefresh();
            this.timerService.clearTimer();
            this.timerService.setTimer(nextProps.value, nextProps.record.data.timer_start, this.serverTime);
            this.timerService.updateTimer(this.timerStart);
            newValue = this.timerService.toSeconds / 3600;
            this._startTimeRefresh();
        }
        this.state.value = newValue;
    }

    async onWillStart() {
        if (this.state.timerRunning) {
            this.serverTime = await this.timerService.getServerTime();
            this.timerService.computeOffset(this.serverTime);
            this.timerService.setTimer(this.state.value, this.timerStart, this.serverTime);
            this.timerService.updateTimer(this.timerStart);
            this.state.value = this.timerService.toSeconds / 3600;
            this._startTimeRefresh();
        }
    }

    get timerStart() {
        return this.props.record.data.timer_start;
    }

    _startTimeRefresh() {
        if (!this.timeRefresh) {
            this.timeRefresh = setInterval(() => {
                this.timerService.updateTimer(this.timerStart);
                this.state.value = this.timerService.toSeconds / 3600;
            }, 1000);
        }
    }

    _stopTimeRefresh() {
        if (this.timeRefresh) {
            clearTimeout(this.timeRefresh);
            this.timeRefresh = 0;
        }
    }

    get TimesheetTimerFloatTimerFieldProps() {
        return { ...this.props, ...this.state };
    }

}

TimesheetDisplayTimer.template = "timesheet_grid.TimesheetDisplayTimer";

TimesheetDisplayTimer.components = { TimesheetTimerFloatTimerField };

TimesheetDisplayTimer.fieldDependencies = {
    timer_pause: { type: "datetime" },
    timer_start: { type: "datetime" },
};
