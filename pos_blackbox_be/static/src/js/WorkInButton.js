odoo.define('pos_blackbox_be.WorkInButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    const { onWillStart, useState } = owl;

    class WorkInButton extends PosComponent {
        // TODO: add the clock in/out ticket and push it to the blackbox.
        setup() {
            super.setup();
            useListener('click', this.onClick);
            this.state = useState({ status: 0 });
            onWillStart(this.onWillStart);
        }
        async onWillStart() {
            this.state.status = await this.get_user_session_status(this.env.pos.pos_session.id, this.env.pos.pos_session.user_id[0]);
        }
        async onClick() {
            let clocked = await this.get_user_session_status(this.env.pos.pos_session.id, this.env.pos.pos_session.user_id[0]);
            if(!this.state.status && !clocked)
                this.ClockIn();
            if(this.state.status && clocked)
                this.ClockOut();
        }
        async ClockIn() {
            let users_logged = await this.set_user_session_status(this.env.pos.pos_session.id, this.env.pos.pos_session.user_id[0], true);
            if(users_logged) {
                this.env.pos.pos_session.users_clocked_ids = users_logged;
                this.state.status = true;
            }
        }
        async ClockOut() {
            let unpaid_tables = this.env.pos.db.load('unpaid_orders', []).filter(function (order) { return order.data.amount_total > 0; }).map(function (order) { return order.data.table; });
            if(unpaid_tables.length > 0) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t("Fiscal Data Module error"),
                    body: this.env._t("Tables %s still have unpaid orders. You will not be able to clock out until all orders have been paid."),
                });
                return;
            }

            let userLogOut = await this.set_user_session_status(this.env.pos.pos_session.id, this.env.pos.pos_session.user_id[0], false);
            if(userLogOut) {
                this.env.pos.pos_session.users_clocked_ids = userLogOut;
                this.state.status = false;
            }
        }
        async set_user_session_status(session, user, status) {
            return await this.rpc({
                model: 'pos.session',
                method: 'set_user_session_work_status',
                args: [session, user, status],
            });
        }
        async get_user_session_status(session, user) {
            return await this.rpc({
                model: 'pos.session',
                method: 'get_user_session_work_status',
                args: [session, user],
            });
        }
    }
    WorkInButton.template = 'WorkInButton';

    ProductScreen.addControlButton({
        component: WorkInButton,
        condition: function() {
            return true;
        },
    });

    Registries.Component.add(WorkInButton);

    return WorkInButton;
});
