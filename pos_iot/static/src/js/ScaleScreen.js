odoo.define('pos_iot.ScaleScreen', function(require) {
    'use strict';

    const { Gui } = require('point_of_sale.Gui');
    const ScaleScreen = require('point_of_sale.ScaleScreen');
    const Registries = require('point_of_sale.Registries');

    const PosIotScaleScreen = ScaleScreen =>
        class extends ScaleScreen {
            get scale() {
                return this.env.proxy.iot_device_proxies.scale;
            }
            get isManualMeasurement() {
                return this.scale && this.scale.manual_measurement;
            }
            /**
             * @override
             */
            onMounted() {
                this.iot_box = _.find(this.env.proxy.iot_boxes, iot_box => {
                    return iot_box.ip == this.scale._iot_ip;
                });
                this._error = false;
                this.env.proxy.on('change:status', this, async (eh, status) => {
                    if (
                        !this.iot_box.connected ||
                        !status.newValue.drivers.scale ||
                        status.newValue.drivers.scale.status !== 'connected'
                    ) {
                        if (!this._error) {
                            this._error = true;
                            await Gui.showPopup('ErrorPopup', {
                                title: this.env._t('Could not connect to IoT scale'),
                                body: this.env._t(
                                    'The IoT scale is not responding. You should check your connection.'
                                ),
                            });
                        }
                    } else {
                        this._error = false;
                    }
                });
                if (!this.isManualMeasurement) {
                    this.env.proxy_queue.schedule(() =>
                        this.scale.action({ action: 'start_reading' })
                    );
                }
                super.onMounted();
            }
            /**
             * @override
             */
            onWillUnmount() {
                super.onWillUnmount();
                this.env.proxy_queue.schedule(() =>
                    this.scale.action({ action: 'stop_reading' })
                );
                if (this.scale) this.scale.remove_listener();
            }
            measureWeight() {
                this.env.proxy_queue.schedule(() => this.scale.action({ action: 'read_once' }));
            }
            /**
             * @override
             * Completely replace how the original _readScale works.
             */
            _readScale() {
                this.env.proxy_queue.schedule(async () => {
                    await this.scale.add_listener(this._onValueChange.bind(this));
                    await this.scale.action({ action: 'read_once' });
                });
            }
            async _onValueChange(data) {
                if (data.status.status === 'error') {
                    await Gui.showPopup('ErrorTracebackPopup', {
                        title: data.status.message_title,
                        body: data.status.message_body,
                    });
                } else {
                    this.state.weight = data.value;
                }
            }
        };

    Registries.Component.extend(ScaleScreen, PosIotScaleScreen);

    return ScaleScreen;
});
