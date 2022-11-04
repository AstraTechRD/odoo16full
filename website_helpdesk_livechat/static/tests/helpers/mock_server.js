/** @odoo-module **/

import '@mail/../tests/helpers/mock_server'; // ensure mail override is applied first.

import { patch } from '@web/core/utils/patch';
import { MockServer } from '@web/../tests/helpers/mock_server';

patch(MockServer.prototype, 'website_helpdesk_livechat', {
    /**
     * @override
     */
     _mockResUsers_InitMessaging(ids) {
        return Object.assign(
            {},
            this._super(ids),
            {'helpdesk_livechat_active': 1}
        );
    },
});
