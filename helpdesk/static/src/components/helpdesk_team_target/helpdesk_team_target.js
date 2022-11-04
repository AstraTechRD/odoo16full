/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useAutofocus, useService } from '@web/core/utils/hooks';

const { Component, useRef, useState } = owl;

export class HelpdeskTeamTarget extends Component {
    setup() {
        useAutofocus({ refName: 'inputRef', selectAll: true });
        this.inputRef = useRef("inputRef");
        this.notification = useService("notification");
        this.state = useState({
            isFocused: false,
            value: this.props.value,
        });
    }

    /**
     * @private
     */
    _toggleFocus() {
        this.state.isFocused = !this.state.isFocused;
    }

    /**
     * Handle the keydown event on the value input
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputKeydown(ev) {
        if (ev.key === 'Enter') {
            this.inputRef.el.blur();
        }
    }

    /**
     * @private
     */
    async _onValueChange() {
        const inputValue = this.inputRef.el.value;
        const targetValue = parseInt(inputValue);
        if (Number.isNaN(targetValue)) {
            this.notification.add(_t("Please enter a number."), { type: 'danger' });
            return;
        }
        if (targetValue <= 0) {
            this.notification.add(_t("Please enter a positive value."), { type: 'danger' });
            return;
        }
        if (this.props.percentage && targetValue > 100) {
            this.notification.add(_t("Please enter a percentage below 100."), { type: 'danger' });
            return;
        }
        this.state.value = targetValue;
        await this.props.update(targetValue);
    }
}

HelpdeskTeamTarget.props = {
    showDemo: { type: Boolean, optional: true },
    demoClass: { type: String, optional: true},
    update: Function,
    percentage: { type: Boolean, optional: true },
    value: Number,
    hotkey: { type: String, optional: true },
};
HelpdeskTeamTarget.defaultProps = {
    showDemo: false,
    demoClass: '',
    percentage: false,
};

HelpdeskTeamTarget.template = 'helpdesk.HelpdeskTeamTarget';
