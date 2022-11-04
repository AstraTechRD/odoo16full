/** @odoo-module **/

import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';
import {
    afterNextRender,
    start,
} from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from "@web/../tests/helpers/utils";

import { methods } from 'web_mobile.core';

QUnit.module('mail_enterprise', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('messaging_menu_tests.js');

QUnit.test("'backbutton' event should close messaging menu", async function (assert) {
    assert.expect(1);

    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {},
    });
    await start();
    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());

    await afterNextRender(() => {
        // simulate 'backbutton' event triggered by the mobile app
        const backButtonEvent = new Event('backbutton');
        document.dispatchEvent(backButtonEvent);
    });
    assert.doesNotHaveClass(
        document.querySelector('.o_MessagingMenu'),
        'show',
        "messaging menu should be closed after receiving the backbutton event"
    );
});

QUnit.test('[technical] messaging menu should properly override the back button', async function (assert) {
    assert.expect(4);

    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {
            assert.step(`overrideBackButton: ${enabled}`);
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_toggler').click()
    );
    assert.verifySteps(
        ['overrideBackButton: true'],
        "the overrideBackButton method should be called with true when the menu is opened"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_toggler').click()
    );
    assert.verifySteps(
        ['overrideBackButton: false'],
        "the overrideBackButton method should be called with false when the menu is closed"
    );
});

});
});
