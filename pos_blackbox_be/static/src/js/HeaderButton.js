odoo.define('pos_blackbox_be.HeaderButton', function(require) {
    'use strict';

    const HeaderButton = require('point_of_sale.HeaderButton');
    const Registries = require('point_of_sale.Registries');

    const PosBlackBoxBeHeaderButton = HeaderButton =>
        class extends HeaderButton {
            async onClick() {
                if(this.env.pos.useBlackBoxBe()) {
                    let status = await this.get_user_session_status(this.env.pos.pos_session.id, this.env.pos.pos_session.user_id[0]);
                    if(status) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t("POS error"),
                            body: this.env._t("You need to clock out before closing the POS."),
                        });
                        return;
                    }
                }
                super.onClick();
            }
            async get_user_session_status(session, user) {
                return await this.rpc({
                    model: 'pos.session',
                    method: 'get_user_session_work_status',
                    args: [session, user],
                });
            }
        }

    Registries.Component.extend(HeaderButton, PosBlackBoxBeHeaderButton);

    return HeaderButton;
});