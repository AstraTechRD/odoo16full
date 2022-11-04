odoo.define('pos_hr_mobile.LoginScreen', function (require) {
    "use strict";

    const Registries = require('point_of_sale.Registries');
    const LoginScreen = require('pos_hr.LoginScreen');
    const BarcodeScanner = require('@web/webclient/barcode/barcode_scanner');

    const LoginScreenMobile = LoginScreen => class extends LoginScreen {
        setup() {
            super.setup();
            this.hasMobileScanner = BarcodeScanner.isBarcodeScannerSupported();
        }

        async open_mobile_scanner() {
            let data;
            try {
                data = await BarcodeScanner.scanBarcode();
            } catch (error) {
                if (error.error && error.error.message) {
                    // Here, we know the structure of the error raised by BarcodeScanner.
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Unable to scan'),
                        body: error.error.message,
                    });
                    return;
                }
                // Just raise the other errors.
                throw error;
            }
            if (data) {
                this.env.barcode_reader.scan(data);
                if ('vibrate' in window.navigator) {
                    window.navigator.vibrate(100);
                }
            } else {
                this.env.services.notification.notify({
                    type: 'warning',
                    message: 'Please, Scan again !',
                });
            }
        }
    };
    Registries.Component.extend(LoginScreen, LoginScreenMobile);

    return LoginScreen;
});
