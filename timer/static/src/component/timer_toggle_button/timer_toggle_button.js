/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class TimerToggleButton extends Component {

    setup() {
        this.orm = useService("orm");
    }

    get buttonClass() {
        const layout = this.props.value ? 'danger' : 'primary';
        return `bg-${layout} text-bg-${layout}`;
    }

    get iconClass() {
        const icon = this.props.value ? "stop" : "play";
        return `fa fa-${icon}-circle`;
    }

    get title() {
        return this.props.value ? _lt("Stop") : _lt("Start");
    }

    async onClick(ev) {
        const context = this.props.record.getFieldContext(this.props.name);
        const action = this.props.value ? "stop" : "start";
        await this.orm.call(
            this.props.record.resModel,
            `action_timer_${action}`,
            [[this.props.record.resId]],
            { context },
            );
        await this.props.record.model.load();
        await this.props.record.model.notify();
    }

}

TimerToggleButton.props = {
    ...standardFieldProps,
};
TimerToggleButton.template = "timer.ToggleButton";
