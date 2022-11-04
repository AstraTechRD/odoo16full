/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('documents', {}, function () {
    QUnit.module('documents_systray_activity_menu_tests.js');

    QUnit.test('activity menu widget: documents request button', async function (assert) {
        assert.expect(4);

        const { click, env } = await start({
            async mockRPC(route, args) {
                if (args.method === 'systray_get_activities') {
                    return [];
                }
            },
        });
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.strictEqual(action, 'documents.action_request_form',
                    "should open the document request form");
            },
        });

        await click('.o_ActivityMenuView_dropdownToggle');
        assert.containsOnce(document.body, '.o_ActivityMenuView_dropdownMenu', "dropdown should be shown");
        assert.containsOnce(document.body, '.o_sys_documents_request');
        await click('.o_sys_documents_request');
        assert.containsNone(document.body, '.o_ActivityMenuView_dropdownMenu', "dropdown should be hidden");
    });
});
