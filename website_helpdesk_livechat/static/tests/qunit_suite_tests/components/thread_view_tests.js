/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('website_helpdesk_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_view_tests.js');

QUnit.test('[technical] /helpdesk command gets a body as kwarg', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_type: 'channel',
        name: "General",
    });
    const mailMessageId1 = pyEnv['mail.message'].create({
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const [mailChannelMemberId] = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId1], ['partner_id', '=', pyEnv.currentPartnerId]]);
    pyEnv['mail.channel.member'].write([mailChannelMemberId], { seen_message_id: mailMessageId1 });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
        mockRPC(route, { model, method, kwargs }) {
            if (model === 'mail.channel' && method === 'execute_command_helpdesk') {
                assert.step(`execute command helpdesk. body: ${kwargs.body}`);
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
    });
    await openDiscuss();

    await insertText('.o_ComposerTextInput_textarea', "/helpdesk something");
    await click('.o_Composer_buttonSend');
    assert.verifySteps([
        'execute command helpdesk. body: /helpdesk something',
    ]);
});

});
});
