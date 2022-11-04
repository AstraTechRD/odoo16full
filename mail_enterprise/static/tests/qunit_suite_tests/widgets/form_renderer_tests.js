/** @odoo-module **/

import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';
import {
    afterNextRender,
    isScrolledToBottom,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';
import { getFixture } from "@web/../tests/helpers/utils";

import { fields } from 'web.test_utils';
const { editInput } = fields;

QUnit.module('mail_enterprise', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('form_renderer_tests.js', {
    beforeEach() {
        patchUiSize({ size: SIZES.XXL });
    },
});

QUnit.test('Message list loads new messages on scroll', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        display_name: "Partner 11",
        description: [...Array(60).keys()].join('\n'),
    });
    for (let i = 0; i < 60; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'res.partner',
            res_id: resPartnerId1,
        });
    }
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids" />
                </div>
            </form>`,
    };
    const target = getFixture();
    target.classList.add('o_web_client');
    const { afterEvent, openFormView } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/thread/messages') {
                assert.step('/mail/thread/messages');
            }
        },
        serverData: { views },
        target,
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    assert.verifySteps(
        ['/mail/thread/messages'],
        'Initial message fetch should be done'
    );

    const allMessages = document.querySelectorAll('.o_MessageList_message');
    const lastMessage = allMessages[allMessages.length - 1];
    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            const messageList = document.querySelector('.o_Chatter_scrollPanel');
            messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
        },
        message: "should wait until partner 11 thread loaded more messages after scrolling to bottom a first time",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'res.partner' &&
                threadViewer.thread.id === resPartnerId1
            );
        },
    });
    const lastMessageRect = lastMessage.getBoundingClientRect();
    const listRect = document.querySelector('.o_Chatter_scrollPanel').getBoundingClientRect();
    assert.ok(
        lastMessageRect.top > listRect.top && lastMessageRect.bottom < listRect.bottom,
        "The last message should be visible"
    );
    assert.verifySteps(
        ['/mail/thread/messages'],
        'The RPC to load new messages should be done when scrolling to the bottom'
    );

    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            const messageList = document.querySelector('.o_Chatter_scrollPanel');
            messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
        },
        message: "should wait until partner 11 thread loaded more messages after scrolling to bottom a second time",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'res.partner' &&
                threadViewer.thread.id === resPartnerId1
            );
        },
    });
    assert.verifySteps(
        ['/mail/thread/messages'],
        'The RPC to load new messages should be done when scrolling to the bottom'
    );
});

QUnit.test('Message list is scrolled to new message after posting a message', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        activity_ids: [],
        display_name: "Partner 11",
        description: [...Array(60).keys()].join('\n'),
        message_ids: [],
        message_follower_ids: [],
    });
    for (let i = 0; i < 60; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: 'res.partner',
            res_id: resPartnerId1,
        });
    }
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <header>
                    <button name="primaryButton" string="Primary" type="object" class="oe_highlight" />
                </header>
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids" options="{'post_refresh': 'always'}"/>
                </div>
            </form>`,
    };
    const target = getFixture();
    target.classList.add('o_web_client');
    const { afterEvent, openFormView } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.step('/mail/message/post');
            }
        },
        serverData: { views },
        target,
    });
    await openFormView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const controllerContentEl = document.querySelector('.o_content');

    assert.hasClass(document.querySelector('.o_FormRenderer_chatterContainer'), 'o-aside',
        "chatter should be aside"
    );
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "The controller container should not be scrolled"
    );
    assert.strictEqual(document.querySelector('.o_ThreadView_messageList').scrollTop, 0,
        "The top of the message list is visible"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatterTopbar_buttonLogNote').click()
    );
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "The controller container should not be scrolled"
    );

    await afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            const messageList = document.querySelector('.o_Chatter_scrollPanel');
            messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
        },
        message: "should wait until partner 11 thread loaded more messages",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'more-messages-loaded' &&
                threadViewer.thread.model === 'res.partner' &&
                threadViewer.thread.id === resPartnerId1
            );
        },
    });
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            const messageList = document.querySelector('.o_Chatter_scrollPanel');
            messageList.scrollTop = messageList.scrollHeight - messageList.clientHeight;
        },
        message: "should wait until partner 11 thread scrolled to bottom after doing it manually",
        predicate: ({ scrollTop, threadViewer }) => {
            const messageList = document.querySelector('.o_Chatter_scrollPanel');
            return (
                threadViewer.thread.model === 'res.partner' &&
                threadViewer.thread.id === resPartnerId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    const messageList = document.querySelector('.o_Chatter_scrollPanel');
    assert.ok(
        isScrolledToBottom(messageList),
        "The message list should be scrolled to its bottom"
    );

    await afterNextRender(() =>
        editInput(
            document.querySelector('.o_ComposerTextInput_textarea'),
            "New Message"
        )
    );
    assert.verifySteps([], "Message post should not yet be done");

    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
    assert.verifySteps(['/mail/message/post'], "Message post should be done");
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "The controller container should not be scrolled after sending a message"
    );
    assert.strictEqual(document.querySelector('.o_ThreadView_messageList').scrollTop, 0,
        "The top of the message list should be visible after sending a message"
    );
});
});
});
