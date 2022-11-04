/** @odoo-module **/

import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';
import {
    afterNextRender,
    start,
    startServer
} from '@mail/../tests/helpers/test_utils';


QUnit.module('mail_enterprise', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_view_tests.js');

QUnit.test('message list desc order', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ name: 'partner 1' });
    for (let i = 0; i <= 60; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'res.partner',
            res_id: partnerId,
        });
    }
    patchUiSize({ size: SIZES.XXL });
    const { afterEvent, openFormView } = await start();
    await openFormView({
        res_id: partnerId,
        res_model: 'res.partner',
    });

    const messageItems = document.querySelectorAll(`.o_MessageList_item`);
    assert.notOk(
        messageItems[0].classList.contains("o_MessageList_loadMore"),
        "load more link should NOT be before messages"
    );
    assert.ok(
        messageItems[messageItems.length - 1].classList.contains("o_MessageList_loadMore"),
        "load more link should be after messages"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        30,
        "should have 30 messages at the beginning"
    );

    // scroll to bottom
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            const chatterScrollPanel = document.querySelector('.o_Chatter_scrollPanel');
            chatterScrollPanel.scrollTop = chatterScrollPanel.scrollHeight - chatterScrollPanel.clientHeight;
        },
        message: "should wait until channel 1 loaded more messages after scrolling to bottom",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'res.partner' &&
                threadViewer.thread.id === partnerId
            );
        },
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "should have 60 messages after scrolled to bottom"
    );

    await afterNextRender(() => {
        document.querySelector(`.o_ThreadView_messageList`).scrollTop = 0;
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Message`).length,
        60,
        "scrolling to top should not trigger any message fetching"
    );
});
});
});
