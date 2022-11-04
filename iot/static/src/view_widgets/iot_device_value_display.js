/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useIotDevice } from '../iot_device_hook';

const { Component, useState } = owl;

export class IoTDeviceValueDisplay extends Component {
    setup() {
        super.setup();
        this.state = useState({ value: '' });
        useIotDevice({
            getIotIp: () => this.props.record.data.iot_ip,
            getIdentifier: () => this.props.record.data.identifier,
            onValueChange: (data) => {
                this.state.value = data.value;
            },
        });
    }
}
IoTDeviceValueDisplay.template = `iot.IoTDeviceValueDisplay`;

registry.category('view_widgets').add('iot_device_value_display', IoTDeviceValueDisplay);
