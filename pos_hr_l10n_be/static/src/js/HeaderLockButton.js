odoo.define('pos_hr_l10n_be.HeaderLockButton', function(require) {
    'use strict';

    const HeaderLockButton = require('point_of_sale.HeaderLockButton');
    const Registries = require('point_of_sale.Registries');

    const PosHrHeaderLockButton = HeaderLockButton =>
        class extends HeaderLockButton {
            async showLoginScreen() {
                const insz = this.env.pos.get_cashier().insz_or_bis_number;
                if (this.env.pos.config.blackbox_pos_production_id && !insz) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Fiscal Data Module error'),
                        body: this.env._t('INSZ or BIS number not set for current cashier.'),
                    });
                } else if (
                    this.env.pos.config.blackbox_pos_production_id &&
                    this.env.pos.check_if_user_clocked()
                ) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('POS error'),
                        body: this.env._t('You need to clock out before closing the POS.'),
                    });
                } else {
                    await super.showLoginScreen();
                }
            }
        };

    Registries.Component.extend(HeaderLockButton, PosHrHeaderLockButton);

    return HeaderLockButton;
});
