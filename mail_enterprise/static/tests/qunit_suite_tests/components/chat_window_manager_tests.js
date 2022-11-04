/** @odoo-module **/

import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';
import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from "@web/../tests/helpers/utils";

import { methods } from 'web_mobile.core';

QUnit.module('mail_enterprise', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager_tests.js');

QUnit.test("'backbutton' event should close chat window", async function (assert) {
    assert.expect(1);

    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {},
    });

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_member_ids: [[0, 0, {
            is_minimized: true,
            partner_id: pyEnv.currentPartnerId,
        }]],
    });
    await start();
    await afterNextRender(() => {
        // simulate 'backbutton' event triggered by the mobile app
        const backButtonEvent = new Event('backbutton');
        document.dispatchEvent(backButtonEvent);
    });
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "chat window should be closed after receiving the backbutton event"
    );
});

QUnit.test('[technical] chat window should properly override the back button', async function (assert) {
    assert.expect(4);

    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {
            assert.step(`overrideBackButton: ${enabled}`);
        },
    });

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    patchUiSize({ size: SIZES.SM });
    await start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    assert.verifySteps(
        ['overrideBackButton: true'],
        "the overrideBackButton method should be called with true when the chat window is mounted"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandBack').click()
    );
    // The messaging menu is re-open when a chat window is closed,
    // so we need to close it because it overrides the back button too.
    // As long as something overrides the back button, it can't be disabled.
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    assert.verifySteps(
        ['overrideBackButton: false'],
        "the overrideBackButton method should be called with false when the chat window is unmounted"
    );
});

});
});
