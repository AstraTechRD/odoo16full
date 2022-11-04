/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component, useState, onWillStart, onWillUpdateProps } = owl;

export class TimerStartField extends Component {
    setup() {
        super.setup(...arguments);
        this.timerService = useService("timer");
        this.state = useState({ timer: undefined, time: "" });
        onWillStart(async () => {
            this.startTimer(this.props.value);
        });

        onWillUpdateProps(async (nextProps) => {
            clearInterval(this.state.timer);
            this.state.timer = undefined;
            if (nextProps.value && !this.timerPause) {
                if (this.clearTimer) {
                    this.timerService.clearTimer();
                }
                await this.startTimer(nextProps.value);
            } else if (!nextProps.value) {
                this.state.time = "";
            }
        });
    }

    async startTimer(timerStart) {
        if (timerStart) {
            let currentTime;
            if (!("offset" in this.timerService)) {
                if (this.timerPause) {
                    this.clearTimer = true;
                }
                currentTime = this.timerPause || (await this.timerService.getServerTime());
                this.timerService.computeOffset(currentTime);
                this.timerService.setTimer(0, timerStart, currentTime);
            } else {
                this.timerService.updateTimer(timerStart);
            }
            this.state.time = this.timerService.timerFormatted;
            this.state.timer = setInterval(() => {
                if (this.timerPause) {
                    clearInterval(this.state.timer);
                } else {
                    this.timerService.updateTimer(timerStart);
                    this.state.time = this.timerService.timerFormatted;
                }
            }, 1000);
        } else if (!this.timerPause) {
            clearInterval(this.state.timer);
            this.state.time = "";
        }
    }

    get timerPause() {
        return this.props.record.data.timer_pause;
    }
}

TimerStartField.props = {
    ...standardFieldProps,
};
TimerStartField.fieldDependencies = {
    timer_pause: { type: "datetime" },
};
TimerStartField.template = "timer.TimerStartField";

registry.category("fields").add("timer_start_field", TimerStartField);
