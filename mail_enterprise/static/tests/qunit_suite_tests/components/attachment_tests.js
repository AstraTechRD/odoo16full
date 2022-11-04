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
QUnit.module('attachment_tests.js');

QUnit.test("'backbutton' event should close attachment viewer", async function (assert) {
    assert.expect(1);

    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {},
    });

    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: 'channel1',
    });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.png",
        mimetype: 'image/png',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'mail.channel',
        res_id: channelId
    });
    const { openDiscuss } = await start({
        discuss: {
            context: { active_id: channelId },
        },
    });
    await openDiscuss();

    await afterNextRender(() => document.querySelector('.o_AttachmentImage').click());
    await afterNextRender(() => {
        // simulate 'backbutton' event triggered by the mobile app
        const backButtonEvent = new Event('backbutton');
        document.dispatchEvent(backButtonEvent);
    });
    assert.containsNone(
        document.body,
        '.o_Dialog',
        "attachment viewer should be closed after receiving the backbutton event"
    );
});

QUnit.test('[technical] attachment viewer should properly override the back button', async function (assert) {
    assert.expect(4);

    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {
            assert.step(`overrideBackButton: ${enabled}`);
        },
    });

    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ name: 'partner 1' });
    const messageAttachmentId = pyEnv['ir.attachment'].create({
        name: "test.png",
        mimetype: 'image/png',
    });
    pyEnv['mail.message'].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: 'res.partner',
        res_id: partnerId
    });
    const { openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    await afterNextRender(() => document.querySelector('.o_AttachmentImage').click());
    assert.verifySteps(
        ['overrideBackButton: true'],
        "the overrideBackButton method should be called with true when the attachment viewer is mounted"
    );

    await afterNextRender(() =>
        document.querySelector('.o_AttachmentViewer_headerItemButtonClose').click()
    );
    assert.verifySteps(
        ['overrideBackButton: false'],
        "the overrideBackButton method should be called with false when the attachment viewer is unmounted"
    );
});

});
});
