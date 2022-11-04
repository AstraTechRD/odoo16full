odoo.define('account_accountant.MoveLineListViewTests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');

    const { start, startServer } = require('@mail/../tests/helpers/test_utils');
    const { patchUiSize, SIZES } = require('@mail/../tests/helpers/patch_ui_size');
    const { ROUTES_TO_IGNORE: MAIL_ROUTES_TO_IGNORE } = require('@mail/../tests/helpers/webclient_setup');

    const ROUTES_TO_IGNORE = [
        '/bus/im_status',
        '/mail/init_messaging',
        '/mail/load_message_failures',
        '/web/dataset/call_kw/account.move.line/get_views',
        ...MAIL_ROUTES_TO_IGNORE
    ];

    QUnit.module('Views', {}, function () {
        QUnit.module('MoveLineListView', {
            beforeEach: async assert => {
                const pyEnv = await startServer();
                const accountMoveLineIds = pyEnv['account.move.line'].create([
                    { name: "line0" },
                    { name: "line1" },
                    { name: "line2" },
                    { name: "line3" },
                    { name: "line4" },
                    { name: "line5" },
                ]);
                const accountMove = pyEnv['account.move'].create([
                    { name: "move0", invoice_line_ids: [accountMoveLineIds[0], accountMoveLineIds[1]] },
                    { name: "move1", invoice_line_ids: [accountMoveLineIds[2], accountMoveLineIds[3]] },
                    { name: "move2", invoice_line_ids: [accountMoveLineIds[4], accountMoveLineIds[5]] },
                ]);
                const attachmentIds = pyEnv['ir.attachment'].create([
                    { res_id: accountMove[1], res_model: 'account.move', mimetype: 'application/pdf' },
                    { res_id: accountMove[2], res_model: 'account.move', mimetype: 'application/pdf' },
                ]);
                pyEnv['account.move'].write([accountMove[1]], { attachment_ids: [attachmentIds[0]] });
                pyEnv['account.move.line'].write([accountMoveLineIds[0]], { move_id: accountMove[0] });
                pyEnv['account.move.line'].write([accountMoveLineIds[1]], { move_id: accountMove[0] });
                pyEnv['account.move.line'].write([accountMoveLineIds[2]], { move_id: accountMove[1], move_attachment_ids: [attachmentIds[0]] });
                pyEnv['account.move.line'].write([accountMoveLineIds[3]], { move_id: accountMove[1], move_attachment_ids: [attachmentIds[0]] });
                pyEnv['account.move.line'].write([accountMoveLineIds[4]], { move_id: accountMove[2], move_attachment_ids: [attachmentIds[1]] });
                pyEnv['account.move.line'].write([accountMoveLineIds[5]], { move_id: accountMove[2], move_attachment_ids: [attachmentIds[1]] });
            }
        });

        const OpenPreparedView = async (assert, size) => {
            const views = {
                // move_attachment_ids needs to be visible in order for the datas to be fetched
                // This is due to inconsistencies between mock_server and the real server
                'account.move.line,false,list':
                    `<tree editable='bottom' js_class='account_move_line_list'>
                         <field name='id'/>
                         <field name='name'/>
                         <field name='move_id'/>
                         <field name='move_attachment_ids'>
                             <tree>
                                 <field name="mimetype"/>
                             </tree>
                         </field>
                     </tree>`,
            };
            patchUiSize({ size: size });
            const { openView } = await start({
                serverData: { views },
                mockRPC: function (route, args) {
                    if (ROUTES_TO_IGNORE.includes(route)) {
                        return;
                    }
                    if (route.includes('/web/static/lib/pdfjs/web/viewer.html')) {
                        return Promise.resolve();
                    }
                    const method = args.method || route;
                    assert.step(method + '/' + args.model);
                },
            });
            await openView({
                context: {
                    group_by: ['move_id'],
                },
                res_model: 'account.move.line',
                views: [[false, 'list']],
            });
        };

        QUnit.test('No preview on small devices', async assert => {
            await OpenPreparedView(assert, SIZES.XL);

            assert.verifySteps(['web_read_group/account.move.line']);
            assert.containsOnce(document.body, '.o_move_line_list_view', "the class should be set");
            assert.containsNone(document.body, '.o_attachment_preview', "The preview component shouldn't be mounted for small screens");

            const groupLineMoveId = document.querySelectorAll('.o_group_header');
            await testUtils.dom.click(groupLineMoveId[0]);
            assert.verifySteps(["web_search_read/account.move.line"]);
            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[0].querySelectorAll('.o_data_cell')[1]);
            assert.containsNone(document.body, '.o_attachment_preview',
                "The preview component shouldn't be mounted for small screens even when clicking on a line without attachment");

            await testUtils.dom.click(groupLineMoveId[1]);
            assert.verifySteps(["web_search_read/account.move.line", "read/ir.attachment"]);
            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[3].querySelectorAll('.o_data_cell')[1]);
            assert.containsNone(document.body, '.o_attachment_preview',
                "The preview component shouldn't be mounted for small screens even when clicking on a line with attachment");

        });

        QUnit.test('Fetch and preview of attachments on big devices', async assert => {
            await OpenPreparedView(assert, SIZES.XXL);

            assert.verifySteps(['web_read_group/account.move.line']);
            assert.containsOnce(document.body, '.o_move_line_list_view',
                "For the attachment preview to work correctly, this class should be set");
            assert.containsOnce(document.body, '.o_attachment_preview',
                "There should be an attachment preview component loaded");
            assert.containsNone(document.body, '.o_attachment_preview iframe',
                "The attachment preview component shouldn't have any document preview loaded");

            const groupLineMoveId = document.querySelectorAll('.o_group_header');
            await testUtils.dom.click(groupLineMoveId[0]);
            assert.verifySteps(["web_search_read/account.move.line"]);

            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[0].querySelectorAll('.o_data_cell')[1]);
            assert.containsNone(document.body, '.o_attachment_preview iframe',
                "The attachment preview component shouldn't have any document preview loaded");
            assert.containsOnce(document.body, '.o_attachment_preview p',
                "There should be a message explaining why there isn't any document preview loaded");

            await testUtils.dom.click(groupLineMoveId[1]);
            assert.verifySteps(["web_search_read/account.move.line", "read/ir.attachment"]);
            assert.containsOnce(document.body, '.o_attachment_preview p',
                "The message explaining why there isn't any document preview loaded should still be there");

            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[1].querySelectorAll('.o_data_cell')[1]);
            assert.verifySteps([], "no extra rpc should be done");

            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[2].querySelectorAll('.o_data_cell')[1]);
            assert.verifySteps([], "no extra rpc should be done");
            assert.containsNone(document.body, '.o_attachment_preview p', "The explanation message should have disappeared");
            assert.containsOnce(document.body, '.o_attachment_preview iframe', "The previewer should be visible");
            assert.hasAttrValue(document.querySelector('.o_attachment_preview iframe'), 'data-src',
                '/web/static/lib/pdfjs/web/viewer.html?file=/web/content/1?filename%3Dundefined',
                "the src attribute should be correctly set on the iframe");

            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[3].querySelectorAll('.o_data_cell')[1]);
            assert.verifySteps([], "no extra rpc should be done");
            assert.hasAttrValue(document.querySelector('.o_attachment_preview iframe'), 'data-src',
                '/web/static/lib/pdfjs/web/viewer.html?file=/web/content/1?filename%3Dundefined',
                "the src attribute shouldn't change on the iframe");

            await testUtils.dom.click(groupLineMoveId[2]);
            assert.verifySteps(["web_search_read/account.move.line", "read/ir.attachment"]);
            assert.containsOnce(document.body, '.o_attachment_preview iframe', "The previewer should be visible");
            assert.hasAttrValue(document.querySelector('.o_attachment_preview iframe'), 'data-src',
                '/web/static/lib/pdfjs/web/viewer.html?file=/web/content/1?filename%3Dundefined',
                "The previewer content shouldn't change without clicking on another line from another account.move");

            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[4].querySelectorAll('.o_data_cell')[1]);
            assert.verifySteps([], "no extra rpc should be done");
            assert.hasAttrValue(document.querySelector('.o_attachment_preview iframe'), 'data-src',
                '/web/static/lib/pdfjs/web/viewer.html?file=/web/content/2?filename%3Dundefined',
                "The previewer content shouldn't change without clicking on another line from another account.move");

            await testUtils.dom.click(document.querySelectorAll('.o_data_row')[0].querySelectorAll('.o_data_cell')[1]);
            assert.verifySteps([], "no extra rpc should be done");
            assert.containsNone(document.body, '.o_attachment_preview iframe',
                "The previewer should disappear when clicking on line without attachment");
            assert.containsOnce(document.body, '.o_attachment_preview p', "The explanation message should come back");
        });
    });
});
