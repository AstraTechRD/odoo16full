/** @odoo-module */

import { registry } from "@web/core/registry";
import { DateTimeField } from '@web/views/fields/datetime/datetime_field';

const { Component } = owl;

export class WarningTooltip extends Component {
    get tooltipInfo() {
        return JSON.stringify({text: this.props.value});
    }
}
WarningTooltip.template = 'industry_fsm.warning_tooltip';

export class DateTimeWithWarning extends DateTimeField {
    get warning() {
        return this.props.record.data.warning || '';
    }
}
DateTimeWithWarning.components.WarningTooltip = WarningTooltip;
DateTimeWithWarning.template = 'industry_fsm.DateTimeWithWarning';


registry.category('fields').add('task_confirm_date_end_with_warning', DateTimeWithWarning);
