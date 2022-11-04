odoo.define('pos_iot.IoTErrorPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class IoTErrorPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            owl.onMounted(this.onMounted);
        }
        onMounted() {
            this.playSound('error');
        }
    }
    IoTErrorPopup.template = 'IoTErrorPopup';
    IoTErrorPopup.defaultProps = {
        confirmText: 'Ok',
        title: 'Error',
        cancelKey: false,
    };

    Registries.Component.add(IoTErrorPopup);

    return IoTErrorPopup;
});
