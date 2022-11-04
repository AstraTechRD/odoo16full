/** @odoo-module **/

const { Component, useState, useExternalListener } = owl;

const INPUT_KEYS = new Set(['Delete', 'Backspace'].concat('0123456789,'.split('')));

export class PinPopup extends Component {
    setup() {
        super.setup();
        this.state = useState({ buffer: '' });
        this.employee = this.props.popupData.employee;

        useExternalListener(window, 'keyup', this._onKeyUp);
    }

    get inputBuffer() {
        return this.state.buffer.replace(/./g, '•');
    }

    sendInput(key) {
        if (INPUT_KEYS.has(key)) {
            if (key === 'Delete') {
                this.state.buffer = '';
            } else if (key === 'Backspace') {
                this.state.buffer = this.state.buffer.slice(0, -1);
            } else {
                this.state.buffer = this.state.buffer + key;
            }
        }
    }

    cancel() {
        this.props.onClosePopup('PinPopup');
    }

    async confirm() {
        await this.props.onPinValidate(this.employee.id, this.state.buffer);
        this.props.onClosePopup('PinPopup');
    }

    _onKeyUp(ev) {
        if (INPUT_KEYS.has(ev.key)) {
            this.sendInput(ev.key);
        } else if (ev.key === 'Enter') {
            this.confirm();
        } else if (ev.key === 'Escape') {
            this.cancel();
        }
    }

}

PinPopup.template = 'mrp_workorder_hr.PinPopup';
