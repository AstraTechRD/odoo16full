odoo.define('web_studio.ActionEditorActionTests', function (require) {
    "use strict";

    var testUtils = require('web.test_utils');

    const { openStudio, registerStudioDependencies } = require("@web_studio/../tests/helpers");
    const { doAction } = require("@web/../tests/webclient/helpers");
    const { getFixture, legacyExtraNextTick } = require("@web/../tests/helpers/utils");
    const { createEnterpriseWebClient } = require("@web_enterprise/../tests/helpers");

    let serverData;
    let target;
    QUnit.module('Studio', {
        beforeEach: function () {
            this.data = {
                kikou: {
                    fields: {
                        display_name: { type: "char", string: "Display Name" },
                        start: { type: 'datetime', store: 'true', string: "start date" },
                    },
                },
                'res.groups': {
                    fields: {
                        display_name: { string: "Display Name", type: "char" },
                    },
                    records: [{
                        id: 4,
                        display_name: "Admin",
                    }],
                },
            };

            const views = {
                "kikou,1,list": `<tree><field name="display_name" /></tree>`,
                "kikou,2,form": `<form><field name="display_name" /></form>`,
                "kikou,false,search": `<search />`,
            };
            serverData = {models: this.data, views};
            target = getFixture();
            registerStudioDependencies();
        }
    }, function () {

        QUnit.module('ActionEditorAction');

        QUnit.test('add a gantt view', async function (assert) {
            assert.expect(5);

            const mockRPC = (route, args) => {
                if (route === '/web_studio/add_view_type') {
                    assert.strictEqual(args.view_type, 'gantt',
                        "should add the correct view");
                    return Promise.resolve(false);
                } else if (args.method === 'fields_get') {
                    assert.strictEqual(args.model, 'kikou',
                        "should read fields on the correct model");
                }
            };

            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            await doAction(webClient, {
                xml_id: "some.xml_id",
                type: "ir.actions.act_window",
                res_model: 'kikou',
                view_mode: 'list',
                views: [[1, 'list'], [2, 'form']],
            }, {clearBreadcrumbs: true});
            await openStudio(target, {noEdit: true});

            await testUtils.dom.click($(target).find('.o_web_studio_view_type[data-type="gantt"] .o_web_studio_thumbnail'));
            await legacyExtraNextTick();

            assert.containsOnce($, '.o_web_studio_new_view_dialog',
                "there should be an opened dialog to select gantt attributes");
            assert.strictEqual($('.o_web_studio_new_view_dialog select[name="date_start"]').val(), 'start',
                "date start should be prefilled (mandatory)");
            assert.strictEqual($('.o_web_studio_new_view_dialog select[name="date_stop"]').val(), 'start',
                "date stop should be prefilled (mandatory)");
        });

        QUnit.test('disable the view from studio', async function (assert) {
            assert.expect(3);

            const actions = {
                1: {
                    id: 1,
                    xml_id: "kikou.action",
                    name: 'Kikou Action',
                    res_model: 'kikou',
                    type: 'ir.actions.act_window',
                    view_mode: 'list,form',
                    views: [[1, 'list'], [2, 'form']],
                }
            };

            const views = {
                'kikou,1,list': `<tree><field name="display_name"/></tree>`,
                'kikou,1,search': `<search></search>`,
                'kikou,2,form': `<form><field name="display_name"/></form>`,
            };
            Object.assign(serverData, {actions, views});

            let loadActionStep = 0;
            const mockRPC = (route, args) => {
                if (route === '/web_studio/edit_action') {
                    return true;
                } else if (route === '/web/action/load') {
                    loadActionStep++;
                    /**
                     * step 1: initial action/load
                     * step 2: on disabling list view
                     */
                    if (loadActionStep === 2) {
                        return {
                            name: 'Kikou Action',
                            res_model: 'kikou',
                            view_mode: 'form',
                            type: 'ir.actions.act_window',
                            views: [[2, 'form']],
                            id: 1,
                        };
                    }
                }
            };

            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });

            await doAction(webClient, 1);
            await openStudio(target);

            await testUtils.dom.click(target.querySelector('.o_web_studio_menu_item a'));

            // make list view disable and form view only will be there in studio view
            await testUtils.dom.click($(target).find('div[data-type="list"] .o_web_studio_more'));
            await testUtils.dom.click($(target).find('div[data-type="list"] a[data-action="disable_view"]'));
            // reloadAction = false;
            assert.hasClass(
                $(target).find('div[data-type="list"]'),
                'o_web_studio_inactive',
                "list view should have become inactive");

            // make form view disable and it should prompt the alert dialog
            await testUtils.dom.click($(target).find('div[data-type="form"] .o_web_studio_more'));
            await testUtils.dom.click($(target).find('div[data-type="form"] a[data-action="disable_view"]'));
            assert.containsOnce(
                $,
                '.o_technical_modal',
                "should display a modal when attempting to disable last view");
            assert.strictEqual(
                $('.o_technical_modal .modal-body').text().trim(),
                "You cannot deactivate this view as it is the last one active.",
                "modal should tell that last view cannot be disabled");
        });

        QUnit.test('add groups on action', async function (assert) {
            assert.expect(1);

            const actions = {
                1: {
                    id: 1,
                    xml_id: "some.xml_id",
                    type: "ir.actions.act_window",
                    res_model: 'kikou',
                    view_mode: 'list',
                    views: [[1, 'list'], [2, 'form']],
                },
            };
            Object.assign(serverData, {actions});

            const mockRPC = (route, args) => {
                if (route === '/web_studio/edit_action') {
                    assert.strictEqual(args.args.groups_id[0], 4,
                        "group admin should be applied on action");
                    return Promise.resolve(true);
                }
            };
            const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
            await doAction(webClient, 1, {clearBreadcrumbs: true});
            await openStudio(target, {noEdit: true});

            await testUtils.fields.many2one.clickOpenDropdown('groups_id');
            await testUtils.fields.many2one.clickHighlightedItem('groups_id');
        });
    });

});
