/** @odoo-module **/

import { registry } from '@web/core/registry';
import { FloatField } from '@web/views/fields/float/float_field';
import { useIotDevice } from '@iot/iot_device_hook';

class IoTMeasureRealTimeValue extends FloatField {
    setup() {
        super.setup();
        useIotDevice({
            getIotIp: () => {
                if (this.props.record.data.test_type === 'measure') {
                    return this.props.record.data[this.props.ip_field];
                }
            },
            getIdentifier: () => {
                if (this.props.record.data.test_type === 'measure') {
                    return this.props.record.data[this.props.identifier_field];
                }
            },
            onValueChange: (data) => {
                if (this.env.model.root.isInEdition) {
                    // Only update the value in the record when the record is in edition mode.
                    return this.props.update(data.value);
                }
            },
        });
    }
}
IoTMeasureRealTimeValue.props = {
    ...FloatField.props,
    ip_field: { type: String },
    identifier_field: { type: String },
};
IoTMeasureRealTimeValue.extractProps = ({ field, attrs }) => {
    return {
        ...FloatField.extractProps({ field, attrs }),
        ip_field: attrs.options.ip_field,
        identifier_field: attrs.options.identifier,
    };
};

registry.category('fields').add('iot_measure', IoTMeasureRealTimeValue);
