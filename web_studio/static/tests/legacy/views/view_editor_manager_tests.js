odoo.define('web_studio.ViewEditorManager_tests', function (require) {
"use strict";

const { start, startServer } = require('@mail/../tests/helpers/test_utils');
const { ROUTES_TO_IGNORE } = require('@mail/../tests/helpers/webclient_setup');
const { ImageField } = require("@web/views/fields/image/image_field");

var AbstractFieldOwl = require('web.AbstractFieldOwl');
var ace = require('web_editor.ace');
var concurrency = require('web.concurrency');
var fieldRegistry = require('web.field_registry');
var fieldRegistryOwl = require('web.field_registry_owl');
var framework = require('web.framework');
var ListRenderer = require('web.ListRenderer');
var testUtils = require('web.test_utils');
var { session } = require('@web/session');

var studioTestUtils = require('web_studio.testUtils');

const { patchWithCleanup } = require("@web/../tests/helpers/utils");
const { registerCleanup } = require("@web/../tests/helpers/cleanup");

const { openStudio, registerStudioDependencies } = require("@web_studio/../tests/helpers");
const { getFixture, legacyExtraNextTick, click, dragAndDrop } = require("@web/../tests/helpers/utils");
const { doAction } = require("@web/../tests/webclient/helpers");
const { createEnterpriseWebClient } = require("@web_enterprise/../tests/helpers");
const { MockServer } = require("@web/../tests/helpers/mock_server");
const LegacyMockServer = require('web.MockServer');

const { MapRenderer } = require("@web_map/map_view/map_renderer");

const { registry } = require("@web/core/registry");

const { xml } = owl;

function getCurrentMockServer() {
    return LegacyMockServer.currentMockServer;
}

let serverData;
let target;
let pyEnv;
QUnit.module('web_studio', {}, function () {
QUnit.module('ViewEditorManager', {
    async beforeEach() {
        pyEnv = await startServer();
        this.data = pyEnv.getData();
        const resPartnerId1 = pyEnv['res.partner'].create({ display_name: 'Dustin', avatar_128: 'D Artagnan' });
        const [partnerId1, partnerId2] = pyEnv['partner'].create([
            { display_name: 'jean' },
            { display_name: 'jacques' },
        ]);
        pyEnv['product'].create([
            {
                display_name: 'xpad',
                m2o: partnerId2,
                partner_ids: [partnerId1],
            },
            {
                display_name: 'xpod',
            },
        ]);
        pyEnv['mail.activity'].create({
            name: 'Chhagan',
            request_partner_id: resPartnerId1,
            summary: 'shaktiman',
        });
        pyEnv['ir.model.fields'].create([
            {
                name: "abc",
                ttype: "many2one",
                relation: "coucou",
            },
            {
                name: "def",
                ttype: "many2one",
                relation: "coucou",
            },
            {
                name: 'name',
                model: 'tasks',
                ttype: 'char',
            },
            {
                name: 'description',
                model: 'tasks',
                ttype: 'char',
            },
        ]);
        pyEnv['ir.attachment'].create([{ name: '1.png' }, { name: '2.png' }]);

        registerStudioDependencies();
        serverData = { models: this.data, views: pyEnv.getViews() };
        serverData.actions = {};

        serverData.actions['studio.coucou_action'] = {
            id: 99,
            xml_id: 'studio.coucou_action',
            name: "coucouAction",
            res_model: "coucou",
            type: "ir.actions.act_window",
            views: [[false, 'list']],
        };

        serverData.views["coucou,false,list"] = `<tree></tree>`;
        serverData.views["coucou,false,search"] = `<search></search>`;

        target = getFixture();

        // unblockUI fadeout delay can lead to undesirable elements remaining in the DOM
        // at the end of the test, let's make it synchronous so that this can never happened.
        const originalUnblokcUI = framework.unblockUI;
        framework.unblockUI = () => originalUnblokcUI({ fadeOut: 0 });
        registerCleanup(() => framework.unblockUI = originalUnblokcUI);
    },
    afterEach() {
        pyEnv = undefined;
    }
}, function () {

    QUnit.module('List');

    QUnit.test('list editor sidebar', async function (assert) {
        assert.expect(5);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree/>",
        });

        assert.containsOnce(vem, '.o_web_studio_sidebar',
            "there should be a sidebar");
        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_new'),'active',
            "the Add tab should be active in list view");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('.o_web_studio_field_type_container').length, 2,
            "there should be two sections in Add (new & existing fields");

        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));

        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'),'active',
            "the View tab should now be active");
        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties'),'disabled',
            "the Properties tab should now be disabled");

    });

    QUnit.test('search existing fields into sidebar', async function (assert) {
        assert.expect(8);

        const odooCurrentDebugValue = odoo.debug;

        odoo.debug = true;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree/>",
        });

        assert.containsOnce(vem, '.o_web_studio_sidebar',
            "there should be a sidebar");
        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_new'),'active',
            "the Add tab should be active in list view");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('.o_web_studio_field_type_container').length, 2,
            "there should be two sections in Add (new & existing fields");
        assert.containsN(vem,
            '.o_web_studio_field_type_container.o_web_studio_existing_fields div.o_web_studio_component', 12);

        const $input = vem.$('.o_web_studio_sidebar_search_input');

        $input.val("a");
        await testUtils.fields.triggerKeyup($input);
        assert.containsN(vem,
            '.o_web_studio_field_type_container.o_web_studio_existing_fields div.o_web_studio_component', 8);

        $input.val("ar");
        await testUtils.fields.triggerKeyup($input);
        assert.containsN(vem,
            '.o_web_studio_field_type_container.o_web_studio_existing_fields div.o_web_studio_component', 2);

        $input.val("art");
        await testUtils.fields.triggerKeyup($input);
        assert.containsOnce(vem,
            '.o_web_studio_field_type_container.o_web_studio_existing_fields div.o_web_studio_component');

        $input.val("artt");
        await testUtils.fields.triggerKeyup($input);
        assert.containsNone(vem,
            '.o_web_studio_field_type_container.o_web_studio_existing_fields div.o_web_studio_component');

        odoo.debug = odooCurrentDebugValue;

    });

    QUnit.test('empty list editor', async function (assert) {
        assert.expect(5);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree/>",
        });

        assert.strictEqual(vem.view_type, 'list',
            "view type should be list");
        assert.containsOnce(vem, '.o_web_studio_list_view_editor',
            "there should be a list editor");
        assert.containsOnce(vem, '.o_web_studio_list_view_editor table thead th.o_web_studio_hook',
            "there should be one hook");
        assert.containsNone(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be no node");
        var nbFields = _.size(this.data.coucou.fields);
        assert.strictEqual(vem.$('.o_web_studio_sidebar .o_web_studio_existing_fields').children().length, nbFields,
            "all fields should be available");

    });

    QUnit.test('list editor', async function (assert) {
        assert.expect(3);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
        });

        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be one node");
        assert.containsN(vem, 'table thead th.o_web_studio_hook', 2,
            "there should be two hooks (before & after the field)");
        var nbFields = _.size(this.data.coucou.fields) - 1; // - display_name
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('.o_web_studio_existing_fields').children().length, nbFields,
            "fields that are not already in the view should be available");

    });

    QUnit.test('disable optional field dropdown icon', async function (assert) {
        assert.expect(2);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name' optional='show'/></tree>",
        });

        assert.strictEqual(vem.$('i.o_optional_columns_dropdown_toggle').length, 1,
            'there should be optional field dropdown icon');
        assert.hasClass(vem.$('i.o_optional_columns_dropdown_toggle'), 'text-muted',
            'optional field dropdown icon must be muted');

    });

    QUnit.test('optional field in list editor', async function (assert) {
        assert.expect(1);

        const vem = await studioTestUtils.createViewEditorManager({
            arch: '<tree><field name="display_name"/></tree>',
            model: 'coucou',
        });

        await testUtils.dom.click(vem.$('.o_web_studio_view_renderer .ui-draggable'));
        assert.containsOnce(
            vem,
            '.o_web_studio_sidebar_optional_select',
            "there should be an optional field");

    });

    QUnit.test('new field should come with show as default value of optional', async function (assert) {
        assert.expect(1);

        const arch = "<tree><field name='display_name'/></tree>";
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.attrs.optional,
                        "show", "default value of optional should be 'show'");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_char'), $('.o_web_studio_hook'));

    });

    QUnit.test('new field before a button_group', async function (assert) {
        assert.expect(3);

        const arch = `<tree>
            <button name="action_1" type="object"/>
            <button name="action_2" type="object"/>
            <field name='display_name'/>
        </tree>`;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].type, 'add');
                    assert.strictEqual(args.operations[0].position, 'before');
                    assert.deepEqual(args.operations[0].target, {
                        "tag": "button",
                        "attrs": {
                            "name": "action_1"
                        },
                        "xpath_info": [
                            {
                                "tag": "tree",
                                "indice": 1
                            },
                            {
                                "tag": "button",
                                "indice": 1
                            }
                        ]
                    });
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_char'),
            $('.o_web_studio_hook')[0]);

    });

    QUnit.test('new field after a button_group', async function (assert) {
        assert.expect(3);

        const arch = `<tree>
            <field name='display_name'/>
            <button name="action_1" type="object"/>
            <button name="action_2" type="object"/>
        </tree>`;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].type, 'add');
                    assert.strictEqual(args.operations[0].position, 'after');
                    assert.deepEqual(args.operations[0].target, {
                        "tag": "button",
                        "attrs": {
                            "name": "action_2"
                        },
                        "xpath_info": [
                            {
                                "tag": "tree",
                                "indice": 1
                            },
                            {
                                "tag": "button",
                                "indice": 2
                            }
                        ]
                    });
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_char'),
            $('.o_web_studio_hook')[2]);

    });

    QUnit.test('invisible field in list editor', async function (assert) {
        assert.expect(3);

        const vem = await studioTestUtils.createViewEditorManager({
            arch: '<tree><field invisible="1" name="display_name"/></tree>',
            model: 'coucou',
        });

        await testUtils.dom.click(vem.$('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('#show_invisible'));
        assert.containsOnce(vem, "th[data-name='display_name'].o_web_studio_show_invisible");

        await testUtils.dom.click(vem.$("th[data-name='display_name'].o_web_studio_show_invisible"));
        assert.containsOnce(vem, '#invisible');

        assert.ok(vem.$el[0].querySelector('#invisible').checked);

    });

    QUnit.test('invisible toggle field in list editor', async function (assert) {
        assert.expect(2);

        const operations = [{
            "type": "attributes",
            "target": {
                "tag": "field",
                "attrs": {
                    "name": "display_name"
                },
                "xpath_info": [{
                    "tag": "tree",
                    "indice": 1
                },{
                    "tag": "field",
                    "indice": 1
                }]
            },
            "position": "attributes",
            "node": {
                "tag": "field",
                "attrs": {
                    "invisible": "1",
                    "name": "display_name",
                    "modifiers": {
                        "column_invisible": true
                    }
                },
                "children": []
            },
            "new_attrs": {
                "invisible": "",
                "attrs": "{}"
            }
        }];

        const archReturn = '<tree><field name="display_name" modifiers="{}" attrs="{}"/></tree>';
        const vem = await studioTestUtils.createViewEditorManager({
            arch: '<tree><field invisible="1" name="display_name"/></tree>',
            model: 'coucou',
            mockRPC(route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.deepEqual(args.operations, operations);
                    return getCurrentMockServer()._mockReturnView(archReturn, "coucou");
                }
            }
        });
        await testUtils.dom.click(vem.$('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('#show_invisible'));
        await testUtils.dom.click(vem.$("th[data-name='display_name'].o_web_studio_show_invisible"));
        await testUtils.dom.click(vem.$('#invisible'));

        assert.notOk(vem.$el[0].querySelector('#invisible').checked);

    });

    QUnit.test('widgets with and without description property in sidebar in debug and non-debug mode', async function (assert) {
        assert.expect(4);

        const originalOdooDebug = odoo.debug;
        odoo.debug = false;
        const FieldChar = fieldRegistry.get('char');
        // add widget in fieldRegistry with description and without desciption
        fieldRegistry.add('widgetWithDescription', FieldChar.extend({
            description: "Test Widget",
        }));
        fieldRegistry.add('widgetWithoutDescription', FieldChar.extend({}));

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
        });

        await testUtils.dom.click(vem.$('thead th[data-node-id=1]'));

        assert.containsOnce(vem, '#widget option[value="widgetWithDescription"]',
            "widget with description should be there");
        assert.containsNone(vem, '#widget option[value="widgetWithoutDescription"]',
            "widget without description should not there in non debug mode");

        odoo.debug = true;
        await testUtils.dom.click(vem.$('thead th[data-node-id=1]'));
        assert.containsOnce(vem, '#widget option[value="widgetWithDescription"]',
            "widget with description should be there");
        assert.containsOnce(vem, '#widget option[value="widgetWithoutDescription"]',
            "widget without description should be there in debug mode");

        odoo.debug = originalOdooDebug;
        delete fieldRegistry.map.widgetWithDescription;
        delete fieldRegistry.map.widgetWithoutDescription;
    });

    QUnit.test('visible studio hooks in listview', async function (assert) {
        assert.expect(2);

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: '<tree><field name="display_name"/></tree>',
            async mockRPC(route) {
                if (route === '/web_studio/edit_view') {
                    const arch = `
                        <tree editable='bottom'>
                            <field name='display_name'/>
                        </tree>`;
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        assert.ok(
            vem.$('th.o_web_studio_hook')[0].offsetWidth,
            "studio hooks should be visible in non-editable listview");

        // check the same with editable list 'bottom'
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_view'));
        await testUtils.dom.triggerEvent(vem.$('option[value="bottom"]'), 'change');
        assert.ok(
            vem.$('th.o_web_studio_hook')[0].offsetWidth,
            "studio hooks should be visible in editable 'bottom' listview");

    });

    QUnit.test('sortby and orderby field in sidebar', async function (assert) {
        assert.expect(8);

        let editViewCount = 0;

        this.data.coucou.fields.display_name.store = true;
        this.data.coucou.fields.char_field.store = true;

        let arch = `
            <tree default_order='char_field desc, display_name asc'>
                <field name='display_name'/>
                <field name='char_field'/>
                <field name="start"/>
            </tree>`;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC(route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch = arch;
                    if (editViewCount === 1) {
                        newArch = `
                            <tree default_order='display_name asc'>
                                <field name='display_name'/>
                                <field name='char_field'/>
                                <field name="start"/>
                            </tree>`;
                    } else if (editViewCount === 2) {
                        newArch = `
                            <tree default_order='display_name desc'>
                                <field name='display_name'/>
                                <field name='char_field'/>
                                <field name="start"/>
                            </tree>`;
                    } else if (editViewCount === 3) {
                        newArch = `
                            <tree>
                                <field name='display_name'/>
                                <field name='char_field'/>
                                <field name="start"/>
                            </tree>`;
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });

        await testUtils.dom.click(document.querySelector(".o_web_studio_sidebar .o_web_studio_view"));
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_view select#sort_field', 'Sortby select box should be exist in slidebar.');
        assert.containsN(vem, 'select#sort_field  option[value]', 2, 'Sortby select box should contains 2 fields.');
        assert.strictEqual(vem.$('select#sort_field').val(), 'char_field', 'First field shoud be selected from multiple fields when multiple sorting fields applied on view.');
        assert.strictEqual(vem.$('select#sort_order').val(), 'desc', 'Default order mustbe as per first field selected.');

        await testUtils.fields.editSelect(vem.$('select#sort_field'), 'display_name');
        assert.strictEqual(vem.$('select#sort_order').val(), 'asc', 'Default order should be in ascending order.');
        assert.doesNotHaveClass(vem.$('#sort_order_div'), 'd-none', 'Orderby field must be visible.');

        await testUtils.fields.editSelect(vem.$('select#sort_order'), 'desc');
        assert.strictEqual(vem.$('select#sort_order').val(), 'desc', 'Default order should be in descending order.');

        await testUtils.fields.editSelect(vem.$('select#sort_field'), '');
        assert.hasClass(vem.$('#sort_order_div'), 'd-none', 'Orderby field must be invisible.');

    });

    QUnit.test('widget dropdown in list editor sidebar', async function (assert) {
        assert.expect(7);

        const originalOdooDebug = odoo.debug;
        odoo.debug = false;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: `<tree>
                    <field name='display_name'/>
                    <field name='priority' widget='priority'/>
                </tree>`,
        });

        // select first column and check widget options
        await testUtils.dom.click(vem.$('thead th[data-node-id=1]'));
        assert.strictEqual(
            vem.$('#widget option:selected').text().trim(),
            "Text",
            "Widget name should be Text");

        // select second column and check widget options
        await testUtils.dom.click(vem.$('thead th[data-node-id=2]'));
        assert.strictEqual(
            vem.$('#widget option:selected').text().trim(),
            "Priority",
            "Widget name should be Priority");
        assert.containsNone(
            vem,
            '#widget option[value="label_selection"]',
            "label_selection widget should not be there");

        // check the widgets in debug mode
        odoo.debug = true;

        await testUtils.dom.click(vem.$('thead th[data-node-id=1]'));
        assert.strictEqual(
            vem.$('#widget option:selected').text().trim(),
            "Text (char)",
            "Widget name should be Text (char)");

        await testUtils.dom.click(vem.$('thead th[data-node-id=2]'));
        assert.strictEqual(
            vem.$('#widget option:selected').text().trim(),
            "Priority (priority)",
            "Widget name should be Priority (priority)");
        assert.containsOnce(
            vem,
            '#widget option[value="label_selection"]',
            "label_selection widget should be there");
        assert.strictEqual(
            vem.$('#widget option[value="label_selection"]').text().trim(),
            "label_selection",
            "Widget should have technical name i.e. label_selection as it does not have description");

        odoo.debug = originalOdooDebug;
    });

    QUnit.test('widget without description property in sidebar should be shown a technical name of widget when selected in normal mode', async function (assert) {
        assert.expect(2);

        odoo.debug = false;
        const FieldChar = fieldRegistry.get('char');
        // add widget in fieldRegistry without desciption
        fieldRegistry.add('widgetWithoutDescription', FieldChar.extend({}));

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name' widget='widgetWithoutDescription'/></tree>",
        });

        await testUtils.dom.click(vem.$('thead th[data-node-id=1]'));
        assert.containsOnce(vem, '#widget option[value="widgetWithoutDescription"]', "widget without description should be there");
        assert.strictEqual(vem.$('#widget option:selected').text().trim(), "widgetWithoutDescription", "Widget should have technical name i.e. widgetWithoutDescription as it does not have description");
        delete fieldRegistry.map.widgetWithoutDescription;
    });

    QUnit.test('editing selection field of list of form view', async function(assert) {
        assert.expect(3);

        serverData.actions["studio.coucou_action"].views = [[false, "form"]];
        serverData.views["coucou,false,form"] = `
            <form>
                <group>
                    <field name="product_ids"><tree>
                          <field name="toughness"/>
                      </tree></field>
                  </group>
              </form>`;

        const mockRPC = (route, args) => {
            if (route === '/web_studio/edit_field') {
                assert.strictEqual(args.model_name, "product");
                assert.strictEqual(args.field_name, "toughness");
                assert.deepEqual(args.values, {
                    selection: '[["0","Hard"],["1","Harder"],["Hardest","Hardest"]]',
                });
                return Promise.resolve({});
            }
            if (route === '/web_studio/edit_view') {
                return Promise.resolve({});
            }
            if (route === '/web_studio/get_default_value') {
                return Promise.resolve({});
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // open list view
        await testUtils.dom.click($(target).find('.o_field_one2many'));
        await testUtils.dom.click($(target).find('button.o_web_studio_editX2Many[data-type="list"]'));
        await legacyExtraNextTick();

        // add value to "toughness" selection field
        await testUtils.dom.click($(target).find('th[data-node-id]'));
        await testUtils.dom.click($(target).find('.o_web_studio_edit_selection_values'));
        $('.modal .o_web_studio_selection_new_value input').val('Hardest');
        await testUtils.dom.click($('.modal .o_web_studio_selection_new_value button.o_web_studio_add_selection_value'));
        await testUtils.dom.click($('.modal.o_web_studio_field_modal footer .btn-primary'));
    });

    QUnit.test('deleting selection field value which is linked in other records', async function (assert) {
        assert.expect(8);

        let editCalls = 0;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: `<form>
                <group>
                <field name="priority"/>
                </group>
                </form>`,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_field') {
                    editCalls++;
                    if (editCalls === 1) {
                        // High selection value removed
                        assert.deepEqual(args.values, {
                            selection: '[["1","Low"],["2","Medium"]]',
                        });
                        assert.notOk(args.force_edit, "force_edit is false");
                        return Promise.resolve({
                            records_linked: 3,
                            message: "There are 3 records linked, upon confirming records will be deleted.",
                        });
                    } else if (editCalls === 2) {
                        assert.deepEqual(args.values, {
                            selection: '[["1","Low"],["2","Medium"]]',
                        });
                        assert.ok(args.force_edit, "force_edit is true");
                    }
                    return Promise.resolve({});
                }
                if (route === '/web_studio/edit_view') {
                    return Promise.resolve({});
                }
            },
        });

        await testUtils.dom.click(vem.$('[name="priority"]'));
        await testUtils.dom.click(vem.$('.o_web_studio_edit_selection_values'));
        assert.containsN($('.modal'), ".o_web_studio_selection_editor > li", 3,
            "there should be 2 selection values");

        await testUtils.dom.click($('.modal .o_web_studio_selection_editor > li:eq(2) .o_web_studio_remove_selection_value'));
        assert.containsN($('.modal'), ".o_web_studio_selection_editor > li", 2,
            "there should be 2 selection values");

        await testUtils.dom.click($('.modal button:contains(Confirm)'));
        assert.containsN($(document), '.modal', 2,
            "should contain 2 modals");
        assert.strictEqual($('.modal .o_web_studio_preserve_space').text(),
            "There are 3 records linked, upon confirming records will be deleted.",
            "should have right message");

        await testUtils.dom.click($('.modal:eq(1) button:contains(Ok)'));

    });

    QUnit.test('invisible list editor', async function(assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name' invisible='1'/></tree>",
        });

        assert.containsNone(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be no node");
        assert.containsOnce(vem, 'table thead th.o_web_studio_hook',
            "there should be one hook");

        // click on show invisible
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));

        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be one node (the invisible one)");
        assert.containsN(vem, 'table thead th.o_web_studio_hook', 2,
            "there should be two hooks (before & after the field)");

    });

    QUnit.test('list editor with header and invisible element', async function(assert){
        assert.expect(4)

        var vem = await studioTestUtils.createViewEditorManager({
            model: "mail.activity",
            arch: "<tree string='List'>" +
            "<header><button name=\"action_do_something\" type=\"object\" string=\"The Button\"/></header>" +
            "<field name='name' class=\"my_super_name_class\" />" +
            "<field name='summary' class=\"my_super_description_class\" invisible=\"True\"/>" +
            "</tree>",
        });

        assert.isVisible(vem.$("td.my_super_name_class"), "The name field should be visible");
        assert.containsNone(vem, 'my_super_description_class', "The description field should not exist");

        // click on show invisible
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));

        assert.isVisible(vem.$("td.my_super_name_class"), "The name field should still be visible");
        assert.isVisible(vem.$("td.my_super_description_class"), "The description field should be visible");

    })

    QUnit.test('list editor with invisible element checkbox', async function(assert){
        assert.expect(2)

        await studioTestUtils.createViewEditorManager({
            model: "mail.activity",
            arch: `<tree string='List'>
                    <field name='name' class="my_super_name_class" />
                    <field name='summary' class="my_super_description_class" invisible="True"/>
                </tree>`
        });

        // click on show invisible
        await testUtils.dom.click(document.querySelector('.o_web_studio_sidebar .o_web_studio_view'));
        assert.hasAttrValue(document.querySelector('input#show_invisible'), 'checked', undefined, "show invisible checkbox is not checked");
        await testUtils.dom.click(document.querySelector('.o_web_studio_sidebar input#show_invisible'));
        await testUtils.dom.click(document.querySelector('.o_web_studio_sidebar .o_web_studio_new'));
        await testUtils.dom.click(document.querySelector('.o_web_studio_sidebar .o_web_studio_view'));
        assert.hasAttrValue(document.querySelector('input#show_invisible'), 'checked', 'checked', "show invisible checkbox should be checked");
    });

    QUnit.test('list editor with control node tag', async function(assert) {
        assert.expect(2);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><control><create string='Add a line'/></control></tree>",
        });

        assert.containsNone(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be no node");

        // click on show invisible
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));

        assert.containsNone(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be no nodes (the control is filtered)");

    });

    QUnit.test('list editor invisible to visible on field', async function (assert) {
        assert.expect(3);

        patchWithCleanup(session, {
            user_context: {
                lang: 'fr_FR',
                tz: 'Europe/Brussels',
            },
        });

        var archReturn = '<tree><field name="char_field" modifiers="{}" attrs="{}"/></tree>';

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name'/>" +
                        "<field name='char_field' invisible='1'/>" +
                    "</tree>",
            mockRPC: function(route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.context.tz, 'Europe/Brussels',
                        'The tz from user_context should have been passed');
                    assert.strictEqual(args.context.lang, false,
                        'The lang in context should be false explicitly');
                    assert.ok(!('column_invisible' in args.operations[0].new_attrs),
                            'we shouldn\'t send "column_invisible"');
                    return getCurrentMockServer()._mockReturnView(archReturn, "coucou");
                }
            }
        });

        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));

        // select the second column
        await testUtils.dom.click(vem.$('thead th[data-node-id=2]'));
        // disable invisible
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#invisible'));

    });

    QUnit.test('list editor invisible to visible on field readonly', async function (assert) {
        assert.expect(2);

        var archReturn = '<tree><field name="char_field" readonly="1" attrs="{}" invisible="1" modifiers="{&quot;column_invisible&quot;: true, &quot;readonly&quot;: true}"/></tree>';

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name'/>" +
                        "<field name='char_field' readonly='1'/>" +
                    "</tree>",
            mockRPC: function(route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.ok(!('readonly' in args.operations[0].new_attrs),
                        'we shouldn\'t send "readonly"');
                    assert.equal(args.operations[0].new_attrs.invisible, 1,
                        'we should send "invisible"');
                    return getCurrentMockServer()._mockReturnView(archReturn, "coucou");
                }
            }
        });

        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));

        // select the second column
        await testUtils.dom.click(vem.$('thead th[data-node-id=2]'));
        // disable invisible
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#invisible'));

    });

    QUnit.test('list editor field', async function (assert) {
        assert.expect(5);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
        });

        // click on the field
        await testUtils.dom.click(vem.$('.o_web_studio_list_view_editor [data-node-id]'));

        assert.hasClass(vem.$('.o_web_studio_list_view_editor [data-node-id]'),'o_web_studio_clicked',
            "the column should have the clicked style");

        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties'),'active',
            "the Properties tab should now be active");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should now display the field properties");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the label in sidebar should be Display Name");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "char",
            "the widget in sidebar should be set by default");

    });

    QUnit.test('add group to field', async function (assert) {
        assert.expect(2);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
            mockRPC: function(route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0], {
                        node: {
                            attrs: {name: 'display_name', modifiers: {}},
                            children: [],
                            tag: 'field',
                        },
                        new_attrs: {groups: pyEnv['res.groups'].search([['name', '=', 'Internal User']])},
                        position: 'attributes',
                        target: {
                            attrs: {name: 'display_name'},
                            tag: 'field',
                            xpath_info: [
                                {
                                    indice: 1,
                                    tag: "tree",
                                },
                                {
                                    indice: 1,
                                    tag: "field"
                                }
                            ],
                        },
                        type: 'attributes',
                    }, "the group operation should be correct");
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    const arch = "<tree>"
                            + "<field name='display_name' studio_groups='[{&quot;id&quot;:4, &quot;name&quot;: &quot;Admin&quot;}]'/>"
                        +"</tree>";
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            }
        });

        // click on the field
        await testUtils.dom.click(vem.$('.o_web_studio_list_view_editor [data-node-id]'));

        await testUtils.fields.many2one.clickOpenDropdown('groups');
        await testUtils.fields.many2one.clickHighlightedItem('groups');
        assert.containsOnce(vem, '.o_field_many2manytags[name="groups"] .badge.o_tag_color_0');
    });

    QUnit.test('sorting rows is disabled in Studio', async function (assert) {
        assert.expect(3);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'product',
            arch: "<tree editable='true'> "+
                "<field name='id' widget='handle'/>" +
                "<field name='display_name'/>" +
            "</tree>",
        });

        assert.containsN(vem, '.ui-sortable-handle', 2,
            "the widget handle should be displayed");
        assert.strictEqual(vem.$('.o_data_cell').text(), "xpadxpod",
            "the records should be ordered");

        // Drag and drop the second line in first position
        await testUtils.dom.dragAndDrop(
            vem.$('.ui-sortable-handle').eq(1),
            vem.$('tbody tr').first(),
            {position: 'top'}
        );
        assert.strictEqual(vem.$('.o_data_cell').text(), "xpadxpod",
            "the records should not have been moved (sortable should be disabled in Studio)");

    });

    QUnit.test('List grouped should not be grouped', async function (assert) {
        assert.expect(1);

        pyEnv['coucou'].create([
            { display_name: 'Red Right Hand', priority: '1', croissant: 3 },
            { display_name: 'Hell Broke Luce', priority: '1', croissant: 5 },
        ]);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='croissant' sum='Total Croissant'/></tree>",
            groupBy: ['priority'],
        });

        assert.containsNone(vem, '.o_web_studio_list_view_editor .o_list_table_grouped',
            "The list should not be grouped");

    });

    QUnit.test('move a field in list', async function (assert) {
        assert.expect(3);
        var arch = "<tree>" +
            "<field name='display_name'/>" +
            "<field name='char_field'/>" +
            "<field name='m2o'/>" +
        "</tree>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0], {
                        node: {
                            tag: 'field',
                            attrs: {name: 'm2o'},
                        },
                        position: 'before',
                        target: {
                            tag: 'field',
                            attrs: {name: 'display_name'},
                            xpath_info: [
                                {
                                    indice: 1,
                                    tag: 'tree',
                                },
                                {
                                    indice: 1,
                                    tag: 'field',
                                },
                            ]
                        },
                        type: 'move',
                    }, "the move operation should be correct");
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    const arch = "<tree>" +
                        "<field name='m2o'/>" +
                        "<field name='display_name'/>" +
                        "<field name='char_field'/>" +
                    "</tree>";
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor th').text(), "Display NameA charM2O",
            "the columns should be in the correct order");

        // move the m2o at index 0
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_list_view_editor th:contains(M2O)'),
            vem.$('th.o_web_studio_hook:first'));

        assert.strictEqual(vem.$('.o_web_studio_list_view_editor th').text(), "M2ODisplay NameA char",
            "the moved field should be the first column");

    });

    QUnit.test('list editor field with aggregate function', async function (assert) {
        assert.expect(10);

        pyEnv['coucou'].create([
            { display_name: 'Red Right Hand', croissant: 3 },
            { display_name: 'Hell Broke Luce', croissant: 5 },
        ]);
        var arch = '<tree><field name="display_name"/><field name="croissant"/></tree>';
        var sumArchReturn = '<tree><field name="display_name"/><field name="croissant" sum="Sum of Croissant"/></tree>';
        var avgArchReturn = '<tree><field name="display_name"/><field name="croissant" avg="Average of Croissant"/></tree>';

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function(route, args) {
                if (route === '/web_studio/edit_view') {
                    var op = args.operations[args.operations.length -1];
                    let newArch;
                    if (op.new_attrs.sum !== "") {
                        assert.strictEqual(op.new_attrs.sum, 'Sum of Croissant',
                            '"sum" aggregate should be applied');
                        newArch = sumArchReturn;
                    }
                    else if (op.new_attrs.avg !== "") {
                        assert.strictEqual(op.new_attrs.avg, 'Average of Croissant',
                            '"avg" aggregate should be applied');
                        newArch = avgArchReturn;
                    } else if (op.new_attrs.sum === "" || op.new_attrs.avg == "") {
                        newArch = arch;
                        assert.ok('neither "sum" nor "avg" selected for aggregation');
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            }
        });


        await testUtils.dom.click(vem.$('thead th[data-node-id=1]')); // select the first column

        // selecting column other than float, integer or monetary should not show aggregate selection
        assert.containsNone(vem, '.o_web_studio_sidebar select[name="aggregate"]',
            "should not have aggregate selection for character type column");

        await testUtils.dom.click(vem.$('thead th[data-node-id=2]')); // select the second column
        assert.containsOnce(vem, '.o_web_studio_sidebar select[name="aggregate"]',
            "should have aggregate selection for integer type column");

        // select 'sum' aggregate function
        await testUtils.fields.editAndTrigger(vem.$('.o_web_studio_sidebar').find('select[name="aggregate"]'), 'sum', ['change']);
        assert.strictEqual(vem.$('tfoot tr td.o_list_number').text(), "8",
            "total should be '8'");
        assert.strictEqual(vem.$('tfoot tr td.o_list_number').attr('title'), "Sum of Croissant",
            "title should be 'Sum of Croissant'");

        // select 'avg' aggregate function
        await testUtils.fields.editAndTrigger(vem.$('.o_web_studio_sidebar').find('select[name="aggregate"]'), 'avg', ['change']);
        assert.strictEqual(vem.$('tfoot tr td.o_list_number').text(), "4",
            "total should be '4'");
        assert.strictEqual(vem.$('tfoot tr td.o_list_number').attr('title'), "Average of Croissant",
            "title should be 'Avg of Croissant'");

        // select '' aggregate function
        await testUtils.fields.editAndTrigger(vem.$('.o_web_studio_sidebar').find('select[name="aggregate"]'), '', ['change']);
        assert.strictEqual(vem.$('tfoot tr td.o_list_number').text(), "", "Total should be ''");

    });

    QUnit.module('Form');

    QUnit.test('empty form editor', async function (assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form/>",
        });

        assert.strictEqual(vem.view_type, 'form',
            "view type should be form");
        assert.containsOnce(vem, '.o_web_studio_form_view_editor',
            "there should be a form editor");
        assert.containsNone(vem, '.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable',
            "there should be no node");
        assert.containsNone(vem, '.o_web_studio_form_view_editor .o_web_studio_hook',
            "there should be no hook");

    });

    QUnit.test('form editor', async function (assert) {
        assert.expect(6);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='display_name'/>" +
                    "</sheet>" +
                "</form>",
        });

        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable',
            "there should be one node");
        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o_web_studio_hook',
            "there should be one hook");

        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable'));

        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties'),'active',
            "the Properties tab should now be active");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should now display the field properties");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable'),'o-web-studio-editor--element-clicked',
            "the column should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "char",
            "the widget in sidebar should be set by default");

    });

    QUnit.test('optional field not in form editor', async function (assert) {
        assert.expect(1);

        const vem = await studioTestUtils.createViewEditorManager({
            arch: `<form>
                    <sheet>
                        <field name="display_name"/>
                    </sheet>
                </form>`,
            model: 'coucou',
        });

        await testUtils.dom.click(vem.$('.o_web_studio_view_renderer .o_field_char'));
        assert.containsNone(
            vem,
            '.o_web_studio_sidebar_optional_select',
            "there shouldn't be an optional field");

    });

    QUnit.test('many2one field edition', async function (assert) {
        assert.expect(4);

        const productId1 = pyEnv['product'].create({ display_name: 'A very good product' });
        const coucouId1 = pyEnv['coucou'].create({
            display_name: 'Kikou petite perruche',
            m2o: productId1,
        });

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='m2o'/>" +
                    "</sheet>" +
                "</form>",
            res_id: coucouId1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_action') {
                    throw new Error("The many2one form view should not be opened");
                }
            },
        });

        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable',
            "there should be one node");

        // edit the many2one
        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable'));

        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should now display the field properties");
        assert.containsNone(vem, '.o_web_studio_sidebar select[name="widget"] option[value="selection"]',
            "the widget in selection should not be supported in m2o");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable'),'o-web-studio-editor--element-clicked',
            "the column should have the clicked style");
    });

    QUnit.test('image field edition (change size)', async function (assert) {
        assert.expect(10);

        var arch = "<form>" +
            "<sheet>" +
                "<field name='image' widget='image' options='{\"size\":[0, 90],\"preview_image\":\"coucou\"}'/>" +
            "</sheet>" +
        "</form>";
        const partnerId1 = pyEnv['partner'].create({
            display_name: "kamlesh",
            image: "sulochan",
        });

        patchWithCleanup(ImageField.prototype, {
            setup() {
                this._super();
                owl.onMounted(() => {
                    assert.step(`image, width: ${this.props.width}, height: ${this.props.height}, previewImage: ${this.props.previewImage}`)
                })
            }
        })

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'partner',
            arch: arch,
            res_id: partnerId1,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].new_attrs.options, "{\"size\":[0,270],\"preview_image\":\"coucou\"}",
                        "appropriate options for 'image' widget should be passed");
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    const arch = "<form>" +
                        "<sheet>" +
                            "<field name='image' widget='image' options='{\"size\": [0, 270]}'/>" +
                        "</sheet>" +
                    "</form>";
                    return getCurrentMockServer()._mockReturnView(arch, "partner");
                }
            },
        });


        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o_field_image',
            "there should be one image");
        assert.verifySteps(["image, width: undefined, height: 90, previewImage: coucou"], "the image should have been fetched");

        // edit the image
        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o_field_image'));

        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field select#option_size',
            "the sidebar should display dropdown to change image size");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_size option:selected').val(), "[0,90]",
            "the image size should be correctly selected");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_field_image'),'o-web-studio-editor--element-clicked',
            "image should have the clicked style");

        // change image size to large
        await testUtils.fields.editSelect(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_size'), "[0,270]");

        assert.verifySteps(["image, width: undefined, height: 270, previewImage: undefined"], "the image should have been fetched again");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_size option:selected').val(), "[0,270]",
            "the image size should be correctly selected");
    });

    QUnit.test('signature field edition (change full_name)', async function (assert) {
        assert.expect(8);

        const productId1 = pyEnv['product'].create({});
        pyEnv['coucou'].create({
            display_name:'Jughead',
            m2o: productId1,
        });
        var editViewCount = 0;

        var arch = "<form>" +
            "<group>" +
                "<field name='display_name'/>" +
                "<field name='m2o'/>" +
            "</group>" +
        "</form>";
        var newFieldName;
        var self = this;

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch;
                    if (editViewCount === 1) {
                        assert.strictEqual(args.operations[0].node.attrs.widget, "signature",
                            "'signature' widget should be there on field being dropped");
                        newFieldName = args.operations[0].node.field_description.name;
                        newArch = "<form>" +
                            "<group>" +
                                "<field name='display_name'/>" +
                                "<field name='m2o'/>" +
                                "<field name='" + newFieldName + "' widget='signature'/>" +
                            "</group>" +
                        "</form>";
                        self.data.coucou.fields[newFieldName] = {
                            string: "Signature",
                            type: "binary"
                        };
                    } else if (editViewCount === 2) {
                        assert.strictEqual(args.operations[1].new_attrs.options, "{\"full_name\":\"display_name\"}",
                            "correct options for 'signature' widget should be passed");
                        newArch = "<form>" +
                            "<group>" +
                                "<field name='display_name'/>" +
                                "<field name='m2o'/>" +
                                "<field name='" + newFieldName + "' widget='signature' options='{\"full_name\": \"display_name\"}'/>" +
                            "</group>" +
                        "</form>";
                    } else if (editViewCount === 3) {
                        assert.strictEqual(args.operations[2].new_attrs.options, "{\"full_name\":\"m2o\"}",
                            "correct options for 'signature' widget should be passed");
                        newArch = "<form>" +
                            "<group>" +
                                "<field name='display_name'/>" +
                                "<field name='m2o'/>" +
                                "<field name='" + newFieldName + "' widget='signature' options='{\"full_name\": \"m2o\"}'/>" +
                            "</group>" +
                        "</form>";
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });


        // drag and drop the new signature field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_signature'), vem.$('.o_inner_group .o_web_studio_hook:first'));

        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o_signature',
            "there should be one signature field");

        // edit the signature
        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o_signature'));

        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field select#option_full_name',
            "the sidebar should display dropdown to change 'Auto-complete with' field");

        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_full_name option:selected').val(), "",
            "the auto complete field should be empty by default");


        // change auto complete field to 'display_name'
        await testUtils.fields.editSelect(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_full_name'), "display_name");

        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_full_name option:selected').val(), "display_name",
            "the auto complete field should be correctly selected");

        // change auto complete field to 'm2o'
        await testUtils.fields.editSelect(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_full_name'), "m2o");

        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field select#option_full_name option:selected').val(), "m2o",
            "the auto complete field should be correctly selected");
    });

    QUnit.test('change widget binary to image (check default size)', async function (assert) {
        assert.expect(4);

        var arch = "<form>" +
            "<sheet>" +
                "<field name='image'/>" +
            "</sheet>" +
        "</form>";

        const [partnerId1] = pyEnv['partner'].search([['display_name', '=', 'jean']]);
        pyEnv['partner'].write([partnerId1], { image: 'kikou' });

        var vem = await studioTestUtils.createViewEditorManager({
            serverData,
            model: 'partner',
            arch: arch,
            res_id: partnerId1,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].new_attrs.options, '{"size":[0,90]}',
                        "appropriate default options for 'image' widget should be passed");
                    return getCurrentMockServer()._mockReturnView(arch, "partner");
                }
            },
        });


        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable',
            "there should be one binary field");

        // edit the binary field
        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable'));

        // Change widget from binary to image
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field select#widget',
            "the sidebar should display dropdown to change widget");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable'),'o-web-studio-editor--element-clicked',
            "binary field should have the clicked style");

        // change widget to image
        await testUtils.fields.editSelect(vem.$('.o_web_studio_sidebar_content.o_display_field select#widget'), 'image');
    });

    QUnit.test('integer field should come with 0 as default value', async function(assert) {
        assert.expect(1);

        var arch = "<tree><field name='display_name'/></tree>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.field_description.default_value,
                        '0', "related arg should be correct");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_integer'), $('.o_web_studio_hook'));
        await testUtils.nextTick();
    });

    QUnit.test('invisible form editor', async function (assert) {
        assert.expect(6);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='display_name' invisible='1'/>" +
                        "<group>" +
                            "<field name='m2o' attrs=\"{'invisible': [('id', '!=', '42')]}\"/>" +
                        "</group>" +
                    "</sheet>" +
                "</form>",
        });

        assert.containsNone(vem, '.o_web_studio_form_view_editor .o_field_widget');
        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o-web-studio-editor--element-clickable',
            "the invisible node should not be editable (only the group has a node-id set)");
        assert.containsN(vem, '.o_web_studio_form_view_editor .o_web_studio_hook', 2,
            "there should be two hooks (outside and inside the group");

        // click on show invisible
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));

        assert.containsN(vem, '.o_web_studio_form_view_editor .o_web_studio_show_invisible', 2,
            "there should be one visible nodes (the invisible ones)");
        assert.containsNone(vem, '.o_web_studio_form_view_editor .o_invisible_modifier',
            "there should be no invisible node");
        assert.containsN(vem, '.o_web_studio_form_view_editor .o_web_studio_hook', 3,
            "there should be three hooks");

    });

    QUnit.test('form editor - chatter edition', async function (assert) {
        assert.expect(5);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<field name='display_name'/>" +
                    "</sheet>" +
                    "<div class='oe_chatter'/>" +
                "</form>",
            mockRPC: function(route, args) {
                if (route === '/web_studio/get_email_alias') {
                    return Promise.resolve({email_alias: 'coucou'});
                }
            },
        });

        assert.containsOnce(vem, '.o_web_studio_form_view_editor .o_FormRenderer_chatterContainer',
            "there should be a chatter node");

        // click on the chatter
        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o_FormRenderer_chatterContainer .o_web_studio_overlay'));

        assert.hasClass(vem.$('.o_web_studio_sidebar .o_web_studio_properties'),'active',
            "the Properties tab should now be active");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_chatter',
            "the sidebar should now display the chatter properties");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_FormRenderer_chatterContainer'),'o-web-studio-editor--element-clicked',
            "the chatter should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar input[name="email_alias"]').val(), "coucou",
            "the email alias in sidebar should be fetched");

    });

    QUnit.test('fields without value and label (outside of groups) are shown in form', async function (assert) {
        assert.expect(6);

        const coucouId1 = pyEnv['coucou'].create({ display_name: 'Kikou petite perruche' });

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<group>" +
                            "<field name='id'/>" +
                            "<field name='m2o'/>" +
                        "</group>" +
                        "<field name='display_name'/>" +
                        "<field name='char_field'/>" +
                    "</sheet>" +
                "</form>",
            res_id: coucouId1,
        });

        assert.doesNotHaveClass(vem.$('.o_web_studio_form_view_editor [name="id"]'), 'o_web_studio_widget_empty',
            "non empty field in group should label should not be special");
        assert.doesNotHaveClass(vem.$('.o_web_studio_form_view_editor [name="m2o"]'), 'o_web_studio_widget_empty',
            "empty field in group should have without label should not be special");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor [name="m2o"]'),'o_field_empty',
            "empty field in group should have without label should still have the normal empty class");
        assert.doesNotHaveClass(vem.$('.o_web_studio_form_view_editor [name="display_name"]'), 'o_web_studio_widget_empty',
            "non empty field without label should not be special");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor [name="char_field"]'),'o_web_studio_widget_empty',
            "empty field without label should be special");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor [name="char_field"]').text(), "A char",
            "empty field without label should have its string as label");

    });

    QUnit.test('invisible group in form sheet', async function (assert) {
        assert.expect(8);

        const arch = `<form>
            <sheet>
                <group>
                    <group class="kikou" string="Kikou" modifiers="{&quot;invisible&quot;: true}"/>
                    <group class="kikou2" string='Kikou2'/>
                </group>
            </sheet>
        </form>`;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: `<form>
                    <sheet>
                        <group>
                            <group class="kikou" string='Kikou'/>
                            <group class="kikou2" string='Kikou2'/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.equal(args.operations[0].new_attrs.invisible, 1,
                        'we should send "invisible"');
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        assert.containsN(vem, '.o_inner_group', 2,
            "there should be two groups");

        await testUtils.dom.click(vem.$('.o_inner_group:first'));
        assert.containsOnce(vem.$('.o_web_studio_sidebar'), 'input#invisible',
            "should have invisible checkbox");
        assert.notOk(vem.$('input#invisible').is(":checked"),
            "invisible checkbox should not be checked");

        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#invisible'));
        assert.containsN(vem, '.o_inner_group', 1,
            "there should be one visible group now, kikou group is not rendered");

        assert.containsNone(vem, ".o-web-studio-editor--element-clicked");
        assert.hasClass(vem.$(".o_web_studio_sidebar .o_web_studio_new"), "active");

        await click(vem.$el[0].querySelector(".o_inner_group.kikou2"));
        const $groupInput = vem.$('.o_web_studio_sidebar_content.o_display_group input[name="string"]');
        assert.strictEqual($groupInput.val(), "Kikou2", "the group name in sidebar should be set");

    });

    QUnit.test('correctly display hook in form sheet', async function (assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        // hook here
                        "<group>" +
                            "<group/>" +
                            "<group/>" +
                        "</group>" +
                        // hook here
                        "<group>" +
                            "<group/>" +
                            "<group/>" +
                        "</group>" +
                        // hook here
                    "</sheet>" +
                "</form>",
        });

        assert.containsN(vem, '.o_web_studio_form_view_editor .o_form_sheet > div.o_web_studio_hook', 3,
            "there should be three hooks as children of the sheet");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_form_sheet > div:eq(1)'),'o_web_studio_hook',
            "second div should be a hook");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_form_sheet > div:eq(3)'),'o_web_studio_hook',
            "fourth div should be a hook");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_form_sheet > div:eq(5)'),'o_web_studio_hook',
            "last div should be a hook");

    });

    QUnit.test('correctly display hook below group title', async function (assert) {
        assert.expect(14);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<group>" +
                        "</group>" +
                        "<group string='Kikou2'>" +
                        "</group>" +
                        "<group>" +
                            "<field name='m2o'/>" +
                        "</group>" +
                        "<group string='Kikou'>" +
                            "<field name='id'/>" +
                        "</group>" +
                    "</sheet>" +
                "</form>",
        });


        // first group (without title, without content)
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(0) .o_web_studio_hook').length, 1,
            "there should be 1 hook");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(0) > div:eq(0)'),'o_web_studio_hook',
            "the first div should be a hook");

        // second group (with title, without content)
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(1) .o_web_studio_hook').length, 1,
            "there should be 1 hook");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(1) > div:eq(0)').text(), "Kikou2",
            "the first div is the group title");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(1) > div:eq(1)'),'o_web_studio_hook',
            "The second div should be a hook");

        // third group (without title, with content)
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(2) .o_web_studio_hook').length, 2,
            "there should be 2 hooks");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(2) > div:eq(0)'),'o_web_studio_hook',
            "the first div should be a hook");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(2) > div:eq(1)').text(), "M2O",
            "the second div is the field");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(2) > div:eq(1) > div:eq(2)'),'o_web_studio_hook',
            "the hook should be placed after the field");

        // last group (with title, with content)
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(3) .o_web_studio_hook').length, 2,
            "there should be 2 hooks");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(3) > div:eq(0)').text(), "Kikou",
            "the first div is the group title");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(3) > div:eq(1)'),'o_web_studio_hook',
            "the second div should be a hook");
        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(3) > div:eq(2)').text(), "ID",
            "the third div is the field");
        assert.hasClass(vem.$('.o_web_studio_form_view_editor .o_inner_group:eq(3) > div:eq(2) > div:eq(2)'),'o_web_studio_hook',
            "the hook is after the field");

    });

    QUnit.test('correctly display hook at the end of tabs -- empty group', async function(assert) {
        assert.expect(1);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<notebook>" +
                            "<page string='foo'>" +
                                "<group></group>" +
                            "</page>" +
                        "</notebook>" +
                    "</sheet>" +
                "</form>",
        });

        assert.strictEqual(
            vem.$('.o_web_studio_form_view_editor .o_notebook .tab-pane.active').children().last().attr('class'),
            'o_web_studio_hook',
            'When the page contains only an empty group, last child is a studio hook.'
        );

    });

    QUnit.test('correctly display hook at the end of tabs -- multiple groups with content and an empty group', async function(assert) {
        assert.expect(1);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form>" +
                    "<sheet>" +
                        "<notebook>" +
                            "<page string='foo'>" +
                                "<group>" +
                                    "<field name='m2o'/>" +
                                "</group>" +
                                "<group>" +
                                    "<field name='id'/>" +
                                "</group>" +
                                "<group></group>" +
                            "</page>" +
                        "</notebook>" +
                    "</sheet>" +
                "</form>",
        });

        assert.strictEqual(
            vem.$('.o_web_studio_form_view_editor .o_notebook .tab-pane.active').children().last().attr('class'),
            'o_web_studio_hook',
            'When the page contains multiple groups with content and an empty group, last child is still a studio hook.'
        );

    });

    QUnit.test('notebook edition', async function (assert) {
        assert.expect(9);

        var arch = "<form>" +
            "<sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                "</group>" +
                "<notebook>" +
                    "<page string='Kikou'>" +
                        "<field name='id'/>" +
                    "</page>" +
                "</notebook>" +
            "</sheet>" +
        "</form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.tag, 'page',
                        "a page should be added");
                    assert.strictEqual(args.operations[0].node.attrs.string, 'New Page',
                        "the string attribute should be set");
                    assert.strictEqual(args.operations[0].position, 'inside',
                        "a page should be added inside the notebook");
                    assert.strictEqual(args.operations[0].target.tag, 'notebook',
                        "the target should be the notebook in edit_view");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        assert.containsN(vem, '.o_notebook li', 2,
            "there should be one existing page and a fake one");

        // click on existing tab
        var $page = vem.$('.o_notebook li:first');
        await testUtils.dom.click($page);
        assert.hasClass($page,'o-web-studio-editor--element-clicked', "the page should be clickable");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_page',
            "the sidebar should now display the page properties");
        var $pageInput = vem.$('.o_web_studio_sidebar_content.o_display_page input[name="string"]');
        assert.strictEqual($pageInput.val(), "Kikou", "the page name in sidebar should be set");
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_page .o_groups .o_field_many2manytags').length, 1,
            "the groups should be editable for notebook pages");

        // add a new page
        await testUtils.dom.click(vem.$('.o_notebook li:eq(1) > a'));

    });

    QUnit.test('invisible notebook page in form', async function (assert) {
        assert.expect(9);

        const arch = `<form>
            <sheet>
                <notebook>
                    <page class="kikou" string='Kikou' modifiers="{&quot;invisible&quot;: true}">
                        <field name='id'/>
                    </page>
                    <page class="kikou2" string='Kikou2'>
                        <field name='char_field'/>
                    </page>
                </notebook>
            </sheet>
        </form>`;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: `<form>
                        <sheet>
                            <notebook>
                                <page class="kikou" string='Kikou'>
                                    <field name='id'/>
                                </page>
                                <page class="kikou2" string='Kikou2'>
                                    <field name='char_field'/>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.equal(args.operations[0].new_attrs.invisible, 1,
                        'we should send "invisible"');
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        assert.containsN(vem, '.o_notebook li.o-web-studio-editor--element-clickable', 2,
            "there should be two pages");

        await testUtils.dom.click(vem.$('.o_notebook li:first'));
        assert.containsOnce(vem.$('.o_web_studio_sidebar'), 'input#invisible',
            "should have invisible checkbox");
        assert.notOk(vem.$('input#invisible').is(":checked"),
            "invisible checkbox should not be checked");

        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#invisible'));
        assert.containsN(vem, '.o_notebook li', 2,
            "there should be one visible page and a fake one");
        assert.isNotVisible(vem.$('.o_notebook li .kikou'),
            "there should be an invisible page");

        assert.containsNone(vem, ".o-web-studio-editor--element-clicked");
        assert.hasClass(vem.$(".o_web_studio_sidebar .o_web_studio_new"), "active");

        await click(vem.$el[0].querySelector("li .kikou2"));
        const $pageInput = vem.$('.o_web_studio_sidebar_content.o_display_page input[name="string"]');
        assert.strictEqual($pageInput.val(), "Kikou2", "the page name in sidebar should be set");

    });

    QUnit.test('label edition', async function (assert) {
        assert.expect(9);

        var arch = "<form>" +
            "<sheet>" +
                "<group>" +
                    "<label for='display_name' string='Kikou'/>" +
                    "<div><field name='display_name' nolabel='1'/></div>" +
                "</group>" +
                "<group>" +
                    "<field name='char_field'/>" +
                "</group>" +
            "</sheet>" +
        "</form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0].target, {
                        tag: 'label',
                        attrs: {
                            for: 'display_name',
                        },
                        xpath_info: [
                            {
                                indice: 1,
                                tag: 'form',
                            },
                            {
                                indice: 1,
                                tag: 'sheet',
                            },
                            {
                                indice: 1,
                                tag: 'group',
                            },
                            {
                                indice: 1,
                                tag: 'label',
                            },
                        ],
                    }, "the target should be set in edit_view");
                    assert.deepEqual(args.operations[0].new_attrs, {string: 'Yeah'},
                        "the string attribute should be set in edit_view");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        var $label = $(vem.$('.o_web_studio_form_view_editor label')[0]);
        assert.strictEqual($label.text(), "Kikou",
            "the label should be correctly set");

        await testUtils.dom.click($label);
        assert.hasClass($label,'o-web-studio-editor--element-clicked', "the label should be clickable");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_label',
            "the sidebar should now display the label properties");
        var $labelInput = vem.$('.o_web_studio_sidebar_content.o_display_label input[name="string"]');
        assert.strictEqual($labelInput.val(), "Kikou", "the label name in sidebar should be set");
        await testUtils.fields.editAndTrigger($labelInput, 'Yeah', 'change');

        var $fieldLabel = vem.$('.o_web_studio_form_view_editor label:contains("A char")');
        assert.strictEqual($fieldLabel.length, 1, "there should be a label for the field");
        await testUtils.dom.click($fieldLabel);
        assert.doesNotHaveClass($fieldLabel, 'o-web-studio-editor--element-clicked', "the field label should not be clickable");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should now display the field properties");

    });

    QUnit.test('add a statusbar', async function (assert) {
        assert.expect(8);

        var arch = "<form>" +
            "<sheet>" +
                "<group><field name='display_name'/></group>" +
            "</sheet>" +
        "</form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations.length, 2,
                        "there should be 2 operations (one for statusbar and one for the new field");
                    assert.deepEqual(args.operations[0], {type: 'statusbar'});
                    assert.deepEqual(args.operations[1].target, {tag: 'header'},
                        "the target should be correctly set");
                    assert.strictEqual(args.operations[1].position, 'inside',
                        "the position should be correctly set");
                    assert.deepEqual(args.operations[1].node.attrs, {widget: 'statusbar', options: "{'clickable': '1'}"},
                        "the options should be correctly set");

                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        var $statusbar = vem.$('.o_web_studio_form_view_editor .o_web_studio_statusbar_hook');
        assert.deepEqual($statusbar.length, 1, "there should be a hook to add a statusbar");
        await testUtils.dom.click($statusbar);

        assert.deepEqual($('.o_web_studio_field_modal').length, 1,
            "a modal should be open to create the new selection field");
        assert.deepEqual($('.o_web_studio_selection_editor li').length, 3,
            "there should be 3 pre-filled values for the selection field");
        await testUtils.dom.click($('.modal-footer .btn-primary:first'));

    });

    QUnit.test('move a field in form', async function (assert) {
        assert.expect(3);
        var arch = "<form>" +
            "<sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                    "<field name='char_field'/>" +
                    "<field name='m2o'/>" +
                "</group>" +
            "</sheet>" +
        "</form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0], {
                        node: {
                            tag: 'field',
                            attrs: {name: 'm2o'},
                        },
                        position: 'before',
                        target: {
                            tag: 'field',
                            xpath_info: [
                                {
                                    indice: 1,
                                    tag: 'form',
                                },
                                {
                                    indice: 1,
                                    tag: 'sheet',
                                },
                                {
                                    indice: 1,
                                    tag: 'group',
                                },
                                {
                                    indice: 1,
                                    tag: 'field',
                                },
                            ],
                            attrs: {name: 'display_name'},
                        },
                        type: 'move',
                    }, "the move operation should be correct");
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    const arch = "<form>" +
                        "<sheet>" +
                            "<group>" +
                                "<field name='m2o'/>" +
                                "<field name='display_name'/>" +
                                "<field name='char_field'/>" +
                            "</group>" +
                        "</sheet>" +
                    "</form>";
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_form_sheet').text(), "Display NameA charM2O",
            "the moved field should be the first column");

        // Don't be bothered by transition effects
        vem.el.querySelectorAll(".o_web_studio_hook_separator").forEach(sep => {
            sep.style.setProperty("transition", "none", "important");
        })
        // move m2o before display_name
        await dragAndDrop(vem.$('.o_web_studio_form_view_editor .o-draggable:eq(2)')[0],
            vem.$('.o_inner_group .o_web_studio_hook:first')[0]);

        assert.strictEqual(vem.$('.o_web_studio_form_view_editor .o_form_sheet').text(), "M2ODisplay NameA char",
            "the moved field should be the first column");

    });

    QUnit.test('form editor add avatar image', async function (assert) {
        assert.expect(15);
        const arch = `<form>
                <sheet>
                    <div class='oe_title'>
                        <field name='name'/>
                    </div>
                </sheet>
            </form>`;
        let editViewCount = 0;

        const self = this;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'partner',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch;
                    if (editViewCount === 1) {
                        assert.deepEqual(args.operations[0], {
                            field: 'image',
                            type: 'avatar_image',
                        }, "Proper field name and operation type should be passed");
                        newArch = `<form>
                                <sheet>
                                    <field name='image' widget='image' class='oe_avatar' options='{"preview_image": "image"}'/>
                                    <div class='oe_title'>
                                        <field name='name'/>
                                    </div>
                                </sheet>
                            </form>`;
                    } else if (editViewCount === 2) {
                        assert.deepEqual(args.operations[1], {
                            type: 'remove',
                            target: {
                                tag: "field",
                                attrs: {
                                    name: "image",
                                },
                                xpath_info: [
                                    {
                                        indice: 1,
                                        tag: 'form',
                                    },
                                    {
                                        indice: 1,
                                        tag: 'sheet',
                                    },
                                    {
                                        indice: 1,
                                        tag: 'field',
                                    },
                                ],
                            }
                        }, "Proper field name and operation type should be passed");
                        newArch = arch;
                    } else if (editViewCount === 3) {
                        assert.deepEqual(args.operations[2], {
                            field: '',
                            type: 'avatar_image',
                        }, "Proper field name and operation type should be passed");
                        self.data.partner.fields['x_avatar_image'] = {
                            string: "Image",
                            type: "binary"
                        };
                        newArch = `<form>
                                <sheet>
                                    <field name='x_avatar_image' widget='image' class='oe_avatar' options='{"preview_image": "x_avatar_image"}'/>
                                    <div class='oe_title'>
                                        <field name='name'/>
                                    </div>
                                </sheet>
                            </form>`;
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "partner");
                }
            },
        });

        assert.containsNone(vem, '.o_field_widget.oe_avatar',
            "there should be no avatar image field");
        assert.containsOnce(vem, '.oe_avatar.o_web_studio_avatar',
            "there should be the hook for avatar image");

        // Test with existing field.
        await testUtils.dom.click(vem.$('.oe_avatar.o_web_studio_avatar'));
        assert.strictEqual($('.modal .modal-body select > option').length, 2,
            "there should be two option Field selection drop-down ");
        assert.strictEqual($('.modal .modal-body select > option[value="image"]').length, 1,
            "there should be 'Image' option with proper value set in Field selection drop-down ");
        // add existing image field
        testUtils.fields.editSelect($("select[name='field']"), 'image');
        // Click 'Confirm' Button
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));
        assert.containsOnce(vem, '.o_field_widget.oe_avatar[name="image"]',
            "there should be avatar image with field image");
        assert.containsNone(vem, '.oe_avatar.o_web_studio_avatar',
            "there should be the hook for avatar image");

        // Remove already added field from view to test new image field case.
        await testUtils.dom.click(vem.$('.oe_avatar'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        assert.strictEqual($('.modal-body:first').text(),
            "Are you sure you want to remove this field from the view?",
            "should display the correct message");
        await testUtils.dom.click($('.modal-footer .btn-primary'));
        assert.containsNone(vem, '.o_field_widget.oe_avatar',
            "there should be no avatar image field");
        assert.containsOnce(vem, '.oe_avatar.o_web_studio_avatar',
            "there should be the hook for avatar image");

        // Test with new field.
        await testUtils.dom.click(vem.$('.oe_avatar.o_web_studio_avatar'));
        assert.strictEqual($('.modal .modal-body select > option[value=""]').length, 1,
            "there should be 'New Field' option in Field selection drop-down");
        // add new image field
        testUtils.fields.editSelect($("select[name='field']"), '');
        // Click 'Confirm' Button
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));
        assert.containsOnce(vem, '.o_field_widget.oe_avatar[name="x_avatar_image"]',
            "there should be avatar image with field name x_avatar_image");
        assert.containsNone(vem, '.oe_avatar.o_web_studio_avatar',
            "there should be the hook for avatar image");

    });

    QUnit.test('sidebar for a related field', async function (assert) {
        assert.expect(2);

        this.data.product.fields.related = { type: "char", related: "partner.display_name", string: "myRelatedField"};
        const arch = `<form>
                <sheet>
                    <div class='oe_title'>
                        <field name='related'/>
                    </div>
                </sheet>
            </form>`;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'product',
            arch: arch,
        });

        await testUtils.dom.click(vem.el.querySelector("[name='related']"));
        assert.containsOnce(vem.el, ".o_web_studio_sidebar .o_web_studio_properties.active");
        assert.strictEqual(vem.el.querySelector("input[name='string']").value, "myRelatedField");
    });

    QUnit.test('Phone field in form with SMS', async function (assert) {
        assert.expect(3);

        var arch = "<form><sheet>" +
            "<group>" +
            "<field name='display_name' widget='phone' />" +
            "</group>" +
            "</sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC(route, args) {
                if (route === '/web_studio/edit_view') {
                    return Promise.resolve();
                }
            }
        });

        testUtils.mock.intercept(vem, 'view_change', ev => {
            assert.equal(ev.data.new_attrs.options, '{"enable_sms":false}',
                'Writing the enable_sms option workds');
        });
        await testUtils.dom.click(vem.$('.o_form_label:contains(Display Name)'));
        assert.containsOnce(vem, 'input[name="enable_sms"]');
        assert.ok(vem.$('input[name="enable_sms"]').is(':checked'),
            'By default the boolean should be true');

        await testUtils.dom.click(vem.$('input[name="enable_sms"]'));
    });

    QUnit.test('modification of field appearing multiple times in view', async function (assert) {
        assert.expect(4);

        // the typical case of the same field in a single view is conditional sub-views
        // that use attrs={'invisible': [domain]}
        // if the targeted node is after a hidden view, the hidden one should be ignored / skipped
        var arch = '<form>' +
                       '<group invisible="1">' +
                           '<field name="display_name"/>' +
                       '</group>' +
                       '<group>' +
                           '<field name="display_name"/>' +
                       '</group>' +
                       '<group>' +
                           '<field name="char_field" />' +
                       '</group>' +
                   '</form>'

        const vem = await studioTestUtils.createViewEditorManager({
            arch: arch,
            model: 'coucou',
            debug: true,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0].target.xpath_info, [
                        {
                            tag: 'form',
                            indice: 1,
                        },
                        {
                            tag: 'group',
                            indice: 2,
                        },
                        {
                            tag: 'field',
                            indice: 1,
                        },
                    ], "the target should be the field of the second group");
                    assert.deepEqual(args.operations[0].new_attrs, {string: "Foo"},
                        "the string attribute should be changed from default to 'Foo'");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        var $visibleElement = $(vem.$('.o_web_studio_form_view_editor .o_wrap_label.o-web-studio-editor--element-clickable')[0]);
        assert.strictEqual($visibleElement.text(), "Display Name", "the name should be correctly set");

        await testUtils.dom.click($visibleElement);
        var $labelInput = vem.$('.o_web_studio_sidebar_content input[name="string"]');
        assert.strictEqual($labelInput.val(), "Display Name", "the name in the sidebar should be set");
        await testUtils.fields.editAndTrigger($labelInput, "Foo", ['change']);
    });

    QUnit.module('Kanban');

    QUnit.test('empty kanban editor', async function (assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<kanban>" +
                    "<templates><t t-name='kanban-box'/></templates>" +
                "</kanban>",
        });

        assert.strictEqual(vem.view_type, 'kanban',
            "view type should be kanban");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor',
            "there should be a kanban editor");
        assert.containsNone(vem, '.o_web_studio_kanban_view_editor [data-node-id]',
            "there should be no node");
        assert.containsNone(vem, '.o_web_studio_kanban_view_editor .o_web_studio_hook',
            "there should be no hook");

    });

    QUnit.test('kanban editor', async function (assert) {
        assert.expect(18);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.containsN(vem, '.o_kanban_record', 13);
        assert.containsN(vem, '.o_kanban_record.o_kanban_demo', 6);
        assert.containsN(vem, '.o_kanban_record.o_kanban_ghost', 6);
        assert.doesNotHaveClass(vem.$('.o_kanban_record:first'), 'o_kanban_ghost',
            "first record should not be a ghost");
        assert.doesNotHaveClass(vem.$('.o_kanban_record:first'), 'o_kanban_demo',
            "first record should not be a demo");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor [data-node-id]',
            "there should be one node");
        assert.hasClass(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'),'o_web_studio_widget_empty',
            "the empty node should have the empty class");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor .o_web_studio_hook',
            "there should be one hook");
        assert.containsOnce(vem, '.o_kanban_record .o_web_studio_add_kanban_tags',
            "there should be the hook for tags");
        assert.containsOnce(vem, '.o_kanban_record .o_web_studio_add_dropdown',
            "there should be the hook for dropdown");
        assert.containsOnce(vem, '.o_kanban_record .o_web_studio_add_priority',
            "there should be the hook for priority");
        assert.containsOnce(vem, '.o_kanban_record .o_web_studio_add_kanban_image',
            "there should be the hook for image");

        await testUtils.dom.click(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'));

        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties'),'active',
            "the Properties tab should now be active");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should now display the field properties");
        assert.hasClass(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'),'o_web_studio_clicked',
            "the field should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "char",
            "the widget in sidebar should be set by default");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="display"]').val(), "false",
            "the display attribute should be Default");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the field should have the label Display Name in the sidebar");

    });

    QUnit.test('kanban editor with async widget', async function (assert) {
        var done = assert.async();
        assert.expect(7);

        var fieldDef = testUtils.makeTestPromise();
        var FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('asyncwidget', FieldChar.extend({
            willStart: function () {
                return fieldDef;
            },
        }));

        var prom = studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div><field name='display_name' widget='asyncwidget'/></div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.containsNone(document.body, '.o_web_studio_kanban_view_editor');
        fieldDef.resolve();

        prom.then(async function (vem) {
            assert.containsOnce(document.body, '.o_web_studio_kanban_view_editor');

            assert.containsOnce(vem, '.o_web_studio_kanban_view_editor [data-node-id]');
            assert.containsOnce(vem, '.o_web_studio_kanban_view_editor .o_web_studio_hook');

            await testUtils.dom.click(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'));

            assert.hasClass(vem.$('.o_web_studio_sidebar .o_web_studio_properties'), 'active');
            assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should now display the field properties");
            assert.hasClass(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'), 'o_web_studio_clicked');

            done();
        });
    });

    QUnit.test('changing tab should reset selected_node_id', async function(assert) {
        assert.expect(5);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch : "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name' invisible='1'/>" +
                                "<field name='priority'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        // switch tab to 'view' click on 'show invisible elements'
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));
        assert.containsNone(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'), 'o_web_studio_clicked',
            "the field should not have the clicked style");

        // select field 'display_name'
        await testUtils.dom.click(vem.$('.o_web_studio_kanban_view_editor [data-node-id="1"]'));
        assert.hasClass(vem.$('.o_web_studio_widget_empty[data-node-id="1"]'), 'o_web_studio_clicked',
            "the field should have the clicked style");

        assert.strictEqual(vem.editor.recordEditor.selected_node_id, 1, "selected_node_id should be 1");

        // changing tab (should reset selected_node_id)
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('.o_web_studio_view'));
        assert.strictEqual(vem.editor.recordEditor.selected_node_id, false, "selected_node_id should be false");

        // unchecked 'show invisible'
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));
        assert.containsNone(vem.$('.o_web_studio_widget_empty [data-node-id]'),'o_web_studio_clicked',
            "the field should not have the clicked style");

    });

    QUnit.test('kanban editor show invisible elements', async function(assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch : "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                '<field name="display_name" invisible="1"/>' +
                                '<field name="char_field" modifiers=\'{"invisible": true}\'/>' +
                                '<field name="priority" modifiers=\'{"invisible": [["id", "!=", 1]]}\'/>' +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.containsNone(vem, '.o_web_studio_kanban_view_editor [data-node-id]',
            "there should be no visible node");
        assert.hasAttrValue(vem.$('input#show_invisible'), 'checked', undefined,
            "show invisible checkbox is not checked");

        // click on 'show invisible elements
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar').find('input#show_invisible'));

        assert.containsN(vem, '.o_web_studio_kanban_view_editor [data-node-id]', 3,
            "the 3 invisible fields should be visible now");
        assert.containsN(vem, '.o_web_studio_kanban_view_editor .o_web_studio_show_invisible[data-node-id]', 3,
            "the 3 fields should have the correct class for background");

    });

    QUnit.test('kanban editor add priority', async function (assert) {
        assert.expect(5);
        var arch = "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                                "<field name='priority' widget='priority'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>";

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<kanban>" +
                   "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                   "</templates>" +
                "</kanban>",
            mockRPC: function (route, args) {
                if (route === '/web_studio/get_default_value') {
                    return Promise.resolve({});
                }
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0], {
                        field: 'priority',
                        type: 'kanban_priority',
                    }, "Proper field name and operation type should be passed");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        assert.containsOnce(vem, '.o_kanban_record .o_web_studio_add_priority',
            "there should be the hook for priority");
        // click the 'Add a priority' link
        await testUtils.dom.click(vem.$('.o_kanban_record .o_web_studio_add_priority'));
        assert.strictEqual($('.modal .modal-body select > option[value="priority"]').length, 1,
            "there should be 'Priority' option with proper value set in Field selection drop-down ");
        // select priority field from the drop-down
        $('.modal .modal-body select > option[value="priority"]').prop('selected', true);
        // Click 'Confirm' Button
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));
        assert.containsOnce(vem, '.o_priority', "there should be priority widget in kanban record");
        assert.containsNone(vem, '.o_kanban_record .o_web_studio_add_priority',
            "there should be no priority hook if priority widget exists on kanban");

    });

    QUnit.test('kanban editor no avatar button if already in arch', async function (assert) {
        assert.expect(1);
        const arch = `
        <kanban>
            <templates>
                <field name="partner_id"/>
                <t t-name='kanban-box'>
                    <field name="display_name"/>
                    <img
                        t-if="false"
                        t-att-src="kanban_image('res.partner', 'avatar_128', record.partner_id.raw_value)"
                        class="oe_kanban_avatar"/>
                </t>
            </templates>
        </kanban>
        `;

        this.data.coucou.fields.partner_id = {string: 'Res Partner', type: 'many2one', relation: 'res.partner'};
        this.data.coucou.records = [{ id: 1, display_name: 'Eleven', partner_id: 11}];
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
        });
        assert.containsNone(vem, '.o_web_studio_add_kanban_image',
            "there should be no option to add an avatart");
    });

    QUnit.test('kanban editor add and remove image', async function (assert) {
        assert.expect(8);
        // We have to add relational model specifically named 'res.parter' or
        // 'res.users' because it is hard-coded in the kanban record editor.
        this.data['res.partner'].records.push({
            display_name: 'Dustin',
            id: 1,
            avatar_128: 'D Artagnan',
        });

        this.data.coucou.fields.partner_id = {string: 'Res Partner', type: 'many2one', relation: 'res.partner'};
        this.data.coucou.records = [{ id: 1, display_name: 'Eleven', partner_id: 11 }];


        var arch = "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>";
        var editViewCount = 0;

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/get_default_value') {
                    return Promise.resolve({});
                }
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch;
                    if (editViewCount === 1) {
                        assert.deepEqual(args.operations[0], {
                            field: 'partner_id',
                            type: 'kanban_image',
                        }, "Proper field name and operation type should be passed");
                        newArch = "<kanban>" +
                            "<templates>" +
                                "<t t-name='kanban-box'>" +
                                    "<div class='o_kanban_record'>" +
                                        "<field name='display_name'/>" +
                                        "<div class='oe_kanban_bottom_right'>" +
                                            "<div>test</div>" + // dummy div to make sure img is deleted (otherwise parent div of only child will be deleted)
                                            "<img t-att-src='kanban_image(\"res.partner\", \"avatar_128\", 1)' class='oe_kanban_avatar float-end' width='24' height='24'/>" +
                                        "</div>" +
                                    "</div>" +
                                "</t>" +
                            "</templates>" +
                        "</kanban>";
                    } else if (editViewCount === 2) {
                        assert.strictEqual(args.operations[1].type, 'remove', 'Should have passed correct OP type');
                        assert.strictEqual(args.operations[1].target.tag, 'img', 'Should have correct target tag');
                        assert.deepEqual(args.operations[1].target.xpath_info, [
                            {tag: 'kanban', indice: 1},
                            {tag: 'templates', indice: 1},
                            {tag: 't', indice: 1},
                            {tag: 'div', indice: 1},
                            {tag: 'div', indice: 1},
                            {tag: 'img', indice: 1}],
                            'Should have correct xpath_info as we do not have any tag identifier attribute on image img'
                        );
                        newArch = arch;
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });


        assert.containsOnce(vem, '.o_kanban_record .o_web_studio_add_kanban_image',
            "there should be the hook for Image");
        // click the 'Add a Image' link
        await testUtils.dom.click(vem.$('.o_kanban_record .o_web_studio_add_kanban_image'));
        assert.strictEqual($('.modal .modal-body select > option[value="partner_id"]').length, 1,
            "there should be 'Res Partner' option with proper value set in Field selection drop-down ");
        // Click 'Confirm' Button
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));
        var $img = vem.$('.oe_kanban_bottom_right img.oe_kanban_avatar');
        assert.strictEqual($img.length, 1, "there should be an avatar image");
        // Click on the image
        await testUtils.dom.click($img);
        // remove image from sidebar
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        assert.strictEqual($('.modal-body:first').text(), "Are you sure you want to remove this img from the view?",
            "should display the correct message");
        await testUtils.dom.click($('.modal-footer .btn-primary'));

    });

    QUnit.test('kanban editor with widget', async function (assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name' widget='email'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor [data-node-id]',
            "there should be one node");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor .o_web_studio_hook',
            "there should be one hook");

        await testUtils.dom.click(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'));

        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('select[name="widget"]').val(), "email",
            "the widget in sidebar should be correctly set");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the field should have the label Display Name in the sidebar");

    });

    QUnit.test('grouped kanban editor', async function (assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<kanban default_group_by='display_name'>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.hasClass(vem.$('.o_web_studio_kanban_view_editor'),'o_kanban_grouped',
            "the editor should be grouped");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor [data-node-id]',
            "there should be one node");
        assert.hasClass(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'),'o_web_studio_widget_empty',
            "the empty node should have the empty class");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor .o_web_studio_hook',
            "there should be one hook");

    });

    QUnit.test('grouped kanban editor with record', async function (assert) {
        assert.expect(4);

        this.data.coucou.records = [{
            id: 1,
            display_name: 'coucou 1',
        }];

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<kanban default_group_by='display_name'>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                "<field name='display_name'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>",
        });

        assert.hasClass(vem.$('.o_web_studio_kanban_view_editor'),'o_kanban_grouped',
            "the editor should be grouped");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor [data-node-id]',
            "there should be one node");
        assert.doesNotHaveClass(vem.$('.o_web_studio_kanban_view_editor [data-node-id]'), 'o_web_studio_widget_empty',
            "the empty node should not have the empty class");
        assert.containsOnce(vem, '.o_web_studio_kanban_view_editor .o_web_studio_hook',
            "there should be one hook");

    });

    QUnit.test('Remove a drop-down menu using kanban editor', async function (assert) {
        assert.expect(5);
        var arch =
            '<kanban>' +
                '<templates>' +
                    '<t t-name="kanban-box">' +
                        '<div>' +
                            '<div>' +
                                '<field name="display_name"/>' +
                            '</div>' +
                            '<div class="o_dropdown_kanban dropdown">' +
                                '<a class="dropdown-toggle o-no-caret btn" data-bs-toggle="dropdown" href="#">' +
                                    '<span class="fa fa-bars fa-lg"/>' +
                                '</a>' +
                                '<div class="dropdown-menu" role="menu">' +
                                    '<a type="edit" class="dropdown-item">Edit</a>'+
                                '</div>' +
                            '</div>' +
                        '</div>' +
                    '</t>' +
                '</templates>' +
            '</kanban>';
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].type, 'remove', 'Should have passed correct OP type');
                    assert.strictEqual(args.operations[0].target.tag, 'div', 'Should have correct target tag');
                    assert.deepEqual(args.operations[0].target.xpath_info, [
                        {tag: 'kanban', indice: 1},
                        {tag: 'templates', indice: 1},
                        {tag: 't', indice: 1},
                        {tag: 'div', indice: 1},
                        {tag: 'div', indice: 2}],
                        'Should have correct xpath_info as we do not have any tag identifier attribute on drop-down div'
                    );
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });
        assert.containsOnce(vem, '.o_dropdown_kanban', "there should be one dropdown node");
        await testUtils.dom.click(vem.$('.o_dropdown_kanban'));
        // remove drop-down from sidebar
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        assert.strictEqual($('.modal-body:first').text(), "Are you sure you want to remove this div from the view?",
            "should display the correct message");
        await testUtils.dom.click($('.modal .btn-primary'));
    });

    QUnit.test('kanban editor remove "Set Cover Image" from dropdown menu', async function (assert) {
        assert.expect(1);
        var arch = "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                '<div class="o_dropdown_kanban dropdown">' +
                                    '<a>' +
                                        '<span class="fa fa-ellipsis-v"/>' +
                                    '</a>' +
                                    '<div class="dropdown-menu" role="menu">' +
                                        '<a data-type="set_cover">Set Cover Image</a>' +
                                    "</div>" +
                                "</div>" +
                                "<field name='displayed_image_id' widget='attachment_image'/>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>";

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'partner',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view' && args.operations[0].type === "remove") {
                    assert.deepEqual(args.operations[0], {
                        target: {
                            attrs: {name: 'displayed_image_id'},
                            tag: "field",
                            extra_nodes: [{
                                tag: "a",
                                attrs: {
                                    type: 'set_cover',
                                },
                            }],
                        },
                        type: 'remove',
                    }, "Proper field name and operation type should be passed");
                    return getCurrentMockServer()._mockReturnView(arch, "partner");
                }
            },
        });

        // used to generate fields view in mockRPC
        await testUtils.dom.click(vem.$(".o_kanban_record .o_dropdown_kanban"));
        await testUtils.dom.click(vem.$(".o_display_div .o_web_studio_sidebar_checkbox input"));
    });

    QUnit.test('kanban editor add "Set Cover Image" option in dropdown menu', async function (assert) {
        assert.expect(3);
        var arch = "<kanban>" +
                    "<templates>" +
                        "<t t-name='kanban-box'>" +
                            "<div class='o_kanban_record'>" +
                                '<div class="o_dropdown_kanban dropdown">' +
                                    '<a>' +
                                        '<span class="fa fa-ellipsis-v"/>' +
                                    '</a>' +
                                    '<div class="dropdown-menu" role="menu">' +
                                    "</div>" +
                                "</div>" +
                            "</div>" +
                        "</t>" +
                    "</templates>" +
                "</kanban>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'partner',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0], {field: 'displayed_image_id', type: 'kanban_set_cover'},
                        "Proper field name and operation type should be passed");
                    return getCurrentMockServer()._mockReturnView(arch, "partner");
                }
            },
        });


        await testUtils.dom.click(vem.$(".o_kanban_record .o_dropdown_kanban"));
        assert.hasAttrValue(vem.$('.o_web_studio_sidebar input[name="set_cover"]'), 'checked', undefined,
            "Option to set cover should not be enabled");
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar input[name="set_cover"]'));

        assert.strictEqual($('.modal .modal-body select option[value="displayed_image_id"]').length, 1,
            "there should be option having compatible field (displayed_image_id) Field selection drop-down ");
        // Select the field for cover image
        $('.modal .modal-body select option[value="displayed_image_id"]').prop('selected', true);
        // Click the confirm button
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));

    });

    QUnit.module('Search');

    QUnit.test('empty search editor', async function (assert) {
        assert.expect(6);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<search/>",
        });

        assert.strictEqual(vem.view_type, 'search',
            "view type should be search");
        assert.containsOnce(vem, '.o_web_studio_search_view_editor',
            "there should be a search editor");
        assert.containsOnce(vem, '.o_web_studio_search_autocompletion_fields.table tbody tr.o_web_studio_hook',
            "there should be one hook in the autocompletion fields");
        assert.containsOnce(vem, '.o_web_studio_search_filters.table tbody tr.o_web_studio_hook',
            "there should be one hook in the filters");
        assert.containsOnce(vem, '.o_web_studio_search_group_by.table tbody tr.o_web_studio_hook',
            "there should be one hook in the group by");
        assert.containsNone(vem, '.o_web_studio_search_view_editor [data-node-id]',
            "there should be no node");
    });

    QUnit.test('search editor', async function (assert) {
        assert.expect(14);

        var arch = "<search>" +
                "<field name='display_name'/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<group expand='0' string='Filters'>" +
                    "<filter string='My Name2' " +
                        "name='my_name2' " +
                        "domain='[(\"display_name\",\"=\",coucou2)]'" +
                    "/>" +
                "</group>" +
                "<group expand='0' string='Group By'>" +
                    "<filter name='groupby_display_name' " +
                    "domain='[]' context=\"{'group_by':'display_name'}\"/>" +
                "</group>" +
            "</search>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0].node.attrs, {name: 'display_name'},
                        "we should only specify the name (in attrs) when adding a field");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        // try to add a field in the autocompletion section
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_existing_fields > .ui-draggable[title="Display Name"]'), $('.o_web_studio_search_autocompletion_fields .o_web_studio_hook:first'));

        assert.strictEqual(vem.view_type, 'search',
            "view type should be search");
        assert.containsOnce(vem, '.o_web_studio_search_view_editor',
            "there should be a search editor");
        assert.containsN(vem, '.o_web_studio_search_autocompletion_fields.table tbody tr.o_web_studio_hook', 2,
            "there should be two hooks in the autocompletion fields");
        assert.containsN(vem, '.o_web_studio_search_filters.table tbody tr.o_web_studio_hook', 3,
            "there should be three hook in the filters");
        assert.containsN(vem, '.o_web_studio_search_group_by.table tbody tr.o_web_studio_hook', 2,
            "there should be two hooks in the group by");
        assert.containsOnce(vem, '.o_web_studio_search_autocompletion_fields.table [data-node-id]',
            "there should be 1 node in the autocompletion fields");
        assert.containsN(vem, '.o_web_studio_search_filters.table [data-node-id]', 2,
            "there should be 2 nodes in the filters");
        assert.containsOnce(vem, '.o_web_studio_search_group_by.table [data-node-id]',
            "there should be 1 nodes in the group by");
        assert.containsN(vem, '.o_web_studio_search_view_editor [data-node-id]', 4,
            "there should be 4 nodes");

        // edit the autocompletion field
        await testUtils.dom.click($('.o_web_studio_search_view_editor .o_web_studio_search_autocompletion_container [data-node-id]'));


        assert.hasClass(vem.$('.o_web_studio_sidebar').find('.o_web_studio_properties'),'active',
            "the Properties tab should now be active");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should now display the field properties");
        assert.hasClass(vem.$('.o_web_studio_search_view_editor .o_web_studio_search_autocompletion_container [data-node-id]'),'o_web_studio_clicked',
            "the field should have the clicked style");
        assert.strictEqual(vem.$('.o_web_studio_sidebar').find('input[name="string"]').val(), "Display Name",
            "the field should have the label Display Name in the sidebar");

    });

    QUnit.test('delete a field', async function (assert) {
        assert.expect(3);

        var arch = "<search>" +
                "<field name='display_name'/>" +
            "</search>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0], {
                        target: {
                            attrs: {name: 'display_name'},
                            tag: 'field',
                            xpath_info: [
                                {
                                    indice: 1,
                                    tag: 'search',
                                },
                                {
                                    indice: 1,
                                    tag: 'field',
                                },
                            ],
                        },
                        type: 'remove',
                    });
                    return getCurrentMockServer()._mockReturnView("<search/>", "coucou");
                }
            },
        });


        assert.containsOnce(vem, '[data-node-id]', "there should be one node");
        // edit the autocompletion field
        await testUtils.dom.click(vem.$('.o_web_studio_search_autocompletion_container [data-node-id]'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.containsNone(vem, '[data-node-id]', "there should be no node anymore");

    });

    QUnit.test('indicate that regular stored field(except date/datetime) can not be dropped in "Filters" section', async function (assert) {
        assert.expect(3);

        this.data.coucou.fields.display_name.store = true;
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<search>" +
                "<field name='display_name'/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<group expand='0' string='Filters'>" +
                    "<filter string='My Name2' " +
                        "name='my_name2' " +
                        "domain='[(\"display_name\",\"=\",coucou2)]'" +
                    "/>" +
                "</group>" +
                "<group expand='0' string='Group By'>" +
                    "<filter name='groupby_display_name' " +
                    "domain='[]' context=\"{'group_by':'display_name'}\"/>" +
                "</group>" +
            "</search>",
        });


        // try to add a stored char field in the filters section
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_existing_fields > .ui-draggable[title="Display Name"]'), $('.o_web_studio_search_filters .o_web_studio_hook:first'), {disableDrop: true});

        assert.hasClass(vem.$('.o_web_studio_search_filters'), 'text-muted',
            "filter section should be muted");
        assert.doesNotHaveClass(vem.$('.o_web_studio_search_group_by'), 'text-muted',
            "groupby section should not be muted");
        assert.doesNotHaveClass(vem.$('.o_web_studio_search_autocompletion_fields'), 'text-muted',
            "autocompletion_fields section should not be muted");

    });

    QUnit.test('indicate that ungroupable field can not be dropped in "Filters" and "Group by" sections', async function (assert) {
        assert.expect(3);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<search>" +
                "<field name='display_name'/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<group expand='0' string='Filters'>" +
                    "<filter string='My Name2' " +
                        "name='my_name2' " +
                        "domain='[(\"display_name\",\"=\",coucou2)]'" +
                    "/>" +
                "</group>" +
                "<group expand='0' string='Group By'>" +
                    "<filter name='groupby_display_name' " +
                    "domain='[]' context=\"{'group_by':'display_name'}\"/>" +
                "</group>" +
            "</search>",
        });

        // try to add integer field in groupby
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_existing_fields > .o_web_studio_field_integer:first'), $('.o_web_studio_search_group_by .o_web_studio_hook:first'), {disableDrop: true});

        assert.hasClass(vem.$('.o_web_studio_search_group_by'), 'text-muted',
            "groupby section should be muted");
        assert.hasClass(vem.$('.o_web_studio_search_filters'), 'text-muted',
            "filter section should be muted");
        assert.doesNotHaveClass(vem.$('.o_web_studio_search_autocompletion_fields'), 'text-muted',
            "autocompletion_fields section should be muted");

    });

    QUnit.test('many2many field can be dropped in "Group by" sections', async function (assert) {
        assert.expect(3);

        const arch =
            `<search>
                <field name='display_name'/>
                <filter string='My Name' name='my_name' domain='[("display_name","=",coucou)]' />
                <group expand='0' string='Filters'>
                    <filter string='My Name2' name='my_name2' domain='[("display_name","=",coucou2)]'/>
                </group>
                <group expand='0' string='Group By'>
                    <filter name='groupby_display_name' domain='[]' context="{'group_by':'display_name'}"/>
                    <filter name='groupby_m2m' domain='[]' context="{'group_by':'m2m'}"/>
                </group>
            </search>`;
        this.data.product.fields.m2m.store = true;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'product',
            arch:
                `<search>
                    <field name='display_name'/>
                    <filter string='My Name' name='my_name' domain='[("display_name","=",coucou)]' />
                    <group expand='0' string='Filters'>
                        <filter string='My Name2' name='my_name2' domain='[("display_name","=",coucou2)]'/>
                    </group>
                    <group expand='0' string='Group By'>
                        <filter name='groupby_display_name' domain='[]' context="{'group_by':'display_name'}"/>
                    </group>
                </search>`,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.attrs.context, "{'group_by': 'm2m'}",
                        "should date attribute in attrs when adding a date/datetime field");
                    return getCurrentMockServer()._mockReturnView(arch, "product");
                }
            },
        });

        assert.containsN(vem, '.o_web_studio_search_sub_item .o_web_studio_search_group_by [data-node-id]', 1,
            'should have 1 group inside groupby dropdown');

        // try to add many2many field in groupby
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_existing_fields > .o_web_studio_field_many2many:first'), $('.o_web_studio_search_group_by .o_web_studio_hook:first'));
        assert.containsN(vem, '.o_web_studio_search_sub_item .o_web_studio_search_group_by [data-node-id]', 2,
            'should have 2 group inside groupby dropdown');

    });

    QUnit.test('indicate that separators can not be dropped in "Automcompletion Fields" and "Group by" sections', async function (assert) {
        assert.expect(3);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<search>" +
                "<field name='display_name'/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<group expand='0' string='Filters'>" +
                    "<filter string='My Name2' " +
                        "name='my_name2' " +
                        "domain='[(\"display_name\",\"=\",coucou2)]'" +
                    "/>" +
                "</group>" +
                "<group expand='0' string='Group By'>" +
                    "<filter name='groupby_display_name' " +
                    "domain='[]' context=\"{'group_by':'display_name'}\"/>" +
                "</group>" +
            "</search>",
        });

        // try to add seperator in groupby
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_components > .o_web_studio_filter_separator'), $('.o_web_studio_search_group_by .o_web_studio_hook:first'), {disableDrop: true});
        await testUtils.nextTick();
        assert.hasClass(vem.$('.o_web_studio_search_group_by'), 'text-muted',
            "groupby section should be muted");
        assert.hasClass(vem.$('.o_web_studio_search_autocompletion_fields'),'text-muted',
            "autocompletion_fields section should be muted");
        assert.doesNotHaveClass(vem.$('.o_web_studio_search_filters'), 'text-muted',
            "filter section should not be muted");

    });

    QUnit.test('indicate that filter can not be dropped in "Automcompletion Fields" and "Group by" sections', async function (assert) {
        assert.expect(3);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<search>" +
                    "<field name='display_name'/>" +
                    "<filter string='My Name' " +
                        "name='my_name' " +
                        "domain='[(\"display_name\",\"=\",coucou)]'" +
                    "/>" +
                    "<group expand='0' string='Filters'>" +
                        "<filter string='My Name2' " +
                            "name='my_name2' " +
                            "domain='[(\"display_name\",\"=\",coucou2)]'" +
                        "/>" +
                    "</group>" +
                    "<group expand='0' string='Group By'>" +
                        "<filter name='groupby_display_name' " +
                            "domain='[]' context=\"{'group_by':'display_name'}\"/>" +
                    "</group>" +
                "</search>",
        });

        // try to add seperator in groupby
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_components > .o_web_studio_filter'), $('.o_web_studio_search_group_by .o_web_studio_hook:first'), { disableDrop: true });
        await testUtils.nextTick();
        assert.hasClass(vem.$('.o_web_studio_search_group_by'), 'text-muted',
            "groupby section should be muted");
        assert.hasClass(vem.$('.o_web_studio_search_autocompletion_fields'), 'text-muted',
            "autocompletion_fields section should be muted");
        assert.doesNotHaveClass(vem.$('.o_web_studio_search_filters'), 'text-muted',
            "filter section should not be muted");

    });

    QUnit.test('move a date/datetime field in search filter dropdown', async function (assert) {
        assert.expect(5);

        const arch = "<search>" +
                "<field name='display_name'/>" +
                "<filter string='Start Date' " +
                    "name='start' " +
                    "date='start' " +
                "/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<filter string='My Name2' " +
                    "name='my_name2' " +
                    "domain='[(\"display_name\",\"=\",coucou2)]'" +
                "/>" +
            "</search>";
        this.data.coucou.fields.priority.store = true;
        this.data.coucou.fields.start.store = true;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<search>" +
                "<field name='display_name'/>" +
                "<filter string='My Name' " +
                    "name='my_name' " +
                    "domain='[(\"display_name\",\"=\",coucou)]'" +
                "/>" +
                "<filter string='My Name2' " +
                    "name='my_name2' " +
                    "domain='[(\"display_name\",\"=\",coucou2)]'" +
                "/>" +
            "</search>",
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.attrs.date, 'start',
                        "should date attribute in attrs when adding a date/datetime field");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        assert.containsN(vem, '.o_web_studio_search_sub_item .o_web_studio_search_filters.table tbody tr.o_web_studio_hook', 3,
            "there should be three hooks in the filters dropdown");
        // try to add a field other date/datetime in the filters section
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_existing_fields .o_web_studio_field_selection'), vem.$('.o_web_studio_search_sub_item .o_web_studio_search_filters .o_web_studio_hook').eq(1));
        assert.containsN(vem, '.o_web_studio_search_sub_item .o_web_studio_search_filters [data-node-id]', 2,
            'should have two filters inside filters dropdown');

        // try to add a date field in the filters section
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_existing_fields .o_web_studio_field_datetime[title="Start Date"]'), vem.$('.o_web_studio_search_sub_item .o_web_studio_search_filters .o_web_studio_hook').eq(1));
        assert.containsN(vem, '.o_web_studio_search_sub_item .o_web_studio_search_filters.table tbody tr.o_web_studio_hook', 4,
            "there should be four hooks in the filters dropdown");
        assert.containsN(vem, '.o_web_studio_search_sub_item .o_web_studio_search_filters [data-node-id]', 3,
            'should have three filters inside filters dropdown');

    });

    QUnit.module('Pivot');

    QUnit.test('empty pivot editor', async function (assert) {
        assert.expect(3);
        this.data.coucou.records = [{
            id: 1,
            display_name: 'coucou',
        }];

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<pivot/>",
        });

        assert.strictEqual(vem.view_type, 'pivot',
            "view type should be pivot");
        assert.containsOnce(vem, '.o_pivot',
            "there should be a pivot renderer");
        assert.containsOnce(vem, '.o_pivot > table',
            "the table should be the direct child of pivot");

        await testUtils.dom.click(vem.$('.o_web_studio_sidebar_header [name="view"]'));
    });

    QUnit.test('switching column and row groupby fields in pivot editor', async function (assert) {
        const done = assert.async();
        assert.expect(21);

        let editViewCount = 0;

        this.data.product.fields.display_name.store = true;
        this.data.product.fields.m2o.store = true;
        this.data.product.fields.coucou_id.store = true;
        this.data.product.fields.toughness.store = true;

        let arch = `
            <pivot string='Pipeline Analysis'>
                <field name='m2o' type='col'/>
                <field name='coucou_id' type='row'/>
            </pivot>`;

        const pivot = await studioTestUtils.createViewEditorManager({
            model: 'product',
            arch: arch,
            mockRPC(route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch = arch;
                    if (editViewCount === 1) {
                        assert.strictEqual(args.operations[0].target.field_names[0], "toughness",
                            "targeted field name should be toughness");
                        newArch = `
                            <pivot>
                                <field name='m2o' type='col'/>
                                <field name='coucou_id' type='row'/>
                                <field name='toughness' type='row'/>
                            </pivot>`;
                    } else if (editViewCount === 2) {
                        assert.strictEqual(args.operations[1].target.field_names[0], "display_name",
                            "targeted field name should be display_name");
                        newArch = `
                            <pivot string='Pipeline Analysis' colGroupBys='display_name' rowGroupBys='coucou_id,toughness'>
                                <field name='display_name' type='col'/>
                                <field name='coucou_id' type='row'/>
                                <field name='toughness' type='row'/>
                            </pivot>`;
                    } else if (editViewCount === 3) {
                        assert.strictEqual(args.operations[2].target.field_names[0], "m2o",
                            "targeted field name should be m2o");
                        newArch = `
                            <pivot string='Pipeline Analysis' colGroupBys='display_name' rowGroupBys='m2o'>
                                <field name='display_name' type='col'/>
                                <field name='m2o' type='row'/>
                            </pivot>`;
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "product");
                }
            },
        });

        assert.strictEqual(pivot.view_type, 'pivot', "view type should be pivot");

        return concurrency.delay(100).then(async () => {
            assert.strictEqual(pivot.$('select#column_groupby option:selected').val(), 'm2o',
                "the col field should contain correct value");
            assert.strictEqual(pivot.$('select#first_row_groupby option:selected').val(), 'coucou_id',
                "the row field should contain correct value");

            // set the Row-Second level field value
            await testUtils.fields.editSelect(pivot.$('select#second_row_groupby'), 'toughness');
            assert.strictEqual(pivot.$('select#column_groupby option:selected').val(), 'm2o',
                "the column field should be correctly selected");
            assert.strictEqual(pivot.$('select#first_row_groupby option:selected').val(), 'coucou_id',
                "the first row field should contain correct value");
            assert.strictEqual(pivot.$('select#second_row_groupby option:selected').val(), 'toughness',
                "the second row field should contain correct value");
            assert.strictEqual(pivot.$('th').slice(0, 5).text(), "TotalNonejacques",
                "the col headers should be as expected");
            assert.strictEqual(pivot.$('th').slice(8).text(), "TotalNoneNone",
                "the row headers should be as expected");

            // change the column field value to Display Name
            await testUtils.fields.editSelect(pivot.$('select#column_groupby'), 'display_name');
            assert.strictEqual(pivot.$('select#column_groupby option:selected').val(), 'display_name',
                "the column field should be correctly selected");
            assert.strictEqual(pivot.$('select#first_row_groupby option:selected').val(), 'coucou_id',
                "the first row field should contain correct value");
            assert.strictEqual(pivot.$('select#second_row_groupby option:selected').val(), 'toughness',
                "the second row field should contain correct value");
            assert.strictEqual(pivot.$('th').slice(0, 5).text(), "Totalxpadxpod",
                "the col headers should be as expected");
            assert.strictEqual(pivot.$('th').slice(8).text(), "TotalNoneNone",
                "the row headers should be as expected");

            // change the Row-First level field value to M2O
            await testUtils.fields.editSelect(pivot.$('select#first_row_groupby'), 'm2o');
            assert.strictEqual(pivot.$('select#column_groupby option:selected').val(), 'display_name',
                "the col field should be correctly selected");
            assert.strictEqual(pivot.$('select#first_row_groupby option:selected').val(), 'm2o',
                "the row field should contain correct value");
            assert.strictEqual(pivot.$('select#second_row_groupby option:selected').val(), '',
                "the second row field should contain correct value");
            assert.strictEqual(pivot.$('th').slice(0, 5).text(), "Totalxpadxpod",
                "the col headers should be as expected");
            assert.strictEqual(pivot.$('th').slice(8).text(), "TotalNonejacques",
                "the row headers should be as expected");
            done();
        });
    });

    QUnit.test('column and row date groupbys in pivot editor', async function (assert) {
        const done = assert.async();
        assert.expect(14);

        let editViewCount = 0;

        this.data.coucou.fields.start.store = true;
        this.data.coucou.fields.stop.store = true;
        this.data.coucou.fields.m2o.store = true;
        this.data.coucou.fields.char_field.store = true;

        this.data.coucou.records = [{
            id: 1,
            char_field: 'Hi',
            m2o: 1,
            start: "2016-05-01",
            stop: "2016-05-16",
        }, {
            id: 2,
            char_field: 'Hello',
            m2o: 2,
            start: "2022-09-01",
            stop: "2022-09-16",
        }];

        const arch = `
            <pivot>
                <field name="start" interval="day" type="row"/>
                <field name="stop" interval="year" type="col"/>
            </pivot>
        `;

        const pivot = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC(route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch = arch;
                    if (editViewCount === 1) {
                        assert.strictEqual(args.operations[0].target.field_names[0], "m2o");
                        newArch = `
                            <pivot>
                                <field name='m2o' type='row'/>
                                <field name='stop' type='col'/>
                            </pivot>`;
                    } else if (editViewCount === 2) {
                        assert.strictEqual(args.operations[1].target.field_names[0], "char_field");
                        newArch = `
                            <pivot>
                                <field name='m2o' type='row'/>
                                <field name='char_field' type='col'/>
                            </pivot>`;
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });

        return concurrency.delay(100).then(async () => {
            assert.strictEqual(pivot.$('select#first_row_groupby option:selected').val(), 'start');
            assert.strictEqual(pivot.$('select#column_groupby option:selected').val(), 'stop');

            // change the Row-First level field value to M2O
            await testUtils.fields.editSelect(pivot.$('select#first_row_groupby'), 'm2o');
            assert.strictEqual(pivot.$('select#first_row_groupby option:selected').val(), 'm2o');
            assert.strictEqual(pivot.$('select#second_row_groupby option:selected').val(), '');
            assert.strictEqual(pivot.$('select#column_groupby option:selected').val(), 'stop');
            assert.strictEqual(pivot.$('th').slice(8).text(), "Totalxpadxpod");
            assert.strictEqual(pivot.$('th').slice(0, 5).text(), "TotalMay 2016September 2022");

            // change the column field value to A char
            await testUtils.fields.editSelect(pivot.$('select#column_groupby'), 'char_field');
            assert.strictEqual(pivot.$('select#first_row_groupby option:selected').val(), 'm2o');
            assert.strictEqual(pivot.$('select#second_row_groupby option:selected').val(), '');
            assert.strictEqual(pivot.$('select#column_groupby option:selected').val(), 'char_field');
            assert.strictEqual(pivot.$('th').slice(8).text(), "Totalxpadxpod");
            assert.strictEqual(pivot.$('th').slice(0, 5).text(), "TotalHelloHi");

            pivot.destroy();
            done();
        });
    });

    QUnit.module('Graph');

    QUnit.test('empty graph editor', async function (assert) {
        var done = assert.async();
        assert.expect(3);

        this.data.coucou.records = [{
            id: 1,
            display_name: 'coucou',
        }];

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<graph/>",
        });

        assert.strictEqual(vem.view_type, 'graph',
            "view type should be graph");
        return concurrency.delay(0).then(function () {
            assert.containsOnce(vem, '.o_web_studio_view_renderer .o_graph_renderer');
            assert.containsOnce(vem, '.o_web_studio_view_renderer .o_graph_renderer .o_graph_canvas_container canvas',
                "the graph should be a child of its container");
            done();
        });
    });

    QUnit.test('switching chart types in graph editor', async function (assert) {
        let done = assert.async();
        assert.expect(7);

        let editViewCount = 0;

        this.data.coucou.records = [{
            id: 1,
            display_name: 'stage1',
        }, {
            id: 2,
            display_name: 'stage2',
        }];

        let arch = `
            <graph string='Opportunities'>
                <field name='display_name' type='col'/>
                <field name='char_field' type='row'/>
            </graph>`;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch = arch;
                    if (editViewCount === 1) {
                        newArch = `
                            <graph string='Opportunities' type='line'>
                                <field name='display_name' type='col'/>
                                <field name='char_field' type='row'/>
                            </graph>`;
                    } else if (editViewCount === 2) {
                        newArch = `
                            <graph string='Opportunities' type='pie'>
                                <field name='display_name' type='col'/>
                                <field name='char_field' type='row'/>
                            </graph>`;
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });

        assert.containsN(vem, '.o_web_studio_sidebar_select [name="type"] option', 3, 'Default type contain 3 option');

        return concurrency.delay(100).then(async () => {
            assert.strictEqual(vem.$('select#type option:selected').val(), 'bar',
                "should be display in bar chart mode by default");
            assert.isVisible(vem.el.querySelector('#stacked'), "the stacked graph checkbox should be visible in bar chart");

            // change the type field value to line chart
            await testUtils.fields.editSelect(vem.$('select#type'), 'line');
            assert.strictEqual(vem.view.controllerProps.modelParams.mode, 'line',
                "the default type field should contain line chart");
            assert.isNotVisible(vem.el.querySelector('#stacked'), "the stacked graph checkbox should not be visible in line chart");

            // change the type field value to pie chart
            await testUtils.fields.editSelect(vem.$('select#type'), 'pie');
            assert.strictEqual(vem.view.controllerProps.modelParams.mode, 'pie',
                "the default type field should contain pie chart");
            assert.isNotVisible(vem.el.querySelector('#stacked'), "the stacked graph checkbox should not be visible in pie chart");

            done();
        });
    });

    QUnit.test('date groupbys in graph editor', async function (assert) {
        const done = assert.async();
        assert.expect(8);

        let editViewCount = 0;

        this.data.coucou.fields.start.store = true;
        this.data.coucou.fields.stop.store = true;
        this.data.coucou.fields.m2o.store = true;
        this.data.coucou.fields.char_field.store = true;

        this.data.coucou.records = [{
            id: 1,
            char_field: 'Hi',
            m2o: 1,
            start: "2016-05-01",
            stop: "2016-05-16",
        }, {
            id: 2,
            char_field: 'Hello',
            m2o: 2,
            start: "2022-09-01",
            stop: "2022-09-16",
        }];

        const arch = `
            <graph>
                <field name="start" interval="day"/>
                <field name="stop" interval="year"/>
            </graph>
        `;

        const graph = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC(route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    let newArch = arch;
                    if (editViewCount === 1) {
                        assert.strictEqual(args.operations[0].target.field_names[0], "m2o");
                        newArch = `
                            <graph>
                                <field name="m2o"/>
                                <field name="stop" interval="year"/>
                            </graph>`;
                    } else if (editViewCount === 2) {
                        assert.strictEqual(args.operations[1].target.field_names[0], "char_field");
                        newArch = `
                            <graph>
                                <field name="m2o"/>
                                <field name="char_field"/>
                            </graph>`;
                    }
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });

        return concurrency.delay(100).then(async () => {
            assert.strictEqual(graph.$('select#first_groupby option:selected').val(), 'start');
            assert.strictEqual(graph.$('select#second_groupby option:selected').val(), 'stop');

            await testUtils.fields.editSelect(graph.$('select#first_groupby'), 'm2o');
            assert.strictEqual(graph.$('select#first_groupby option:selected').val(), 'm2o');
            assert.strictEqual(graph.$('select#second_groupby option:selected').val(), 'stop');

            await testUtils.fields.editSelect(graph.$('select#second_groupby'), 'char_field');
            assert.strictEqual(graph.$('select#first_groupby option:selected').val(), 'm2o');
            assert.strictEqual(graph.$('select#second_groupby option:selected').val(), 'char_field');

            graph.destroy();
            done();
        });
    });

    QUnit.module('Gantt');

    QUnit.test('empty gantt editor', async function(assert) {
        assert.expect(4);

        this.data.coucou.records = [];

        const arch = "<gantt date_start='start' date_stop='stop'/>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].new_attrs.precision, '{"day":"hour:quarter"}',
                        "should correctly set the precision");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        assert.strictEqual(vem.view_type, 'gantt',
            "view type should be gantt");
        assert.containsOnce(vem, '.o_web_studio_view_renderer .o_gantt_view',
            "there should be a gantt view");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_view select[name="precision_day"]',
            "it should be possible to edit the day precision");

        vem.$('.o_web_studio_sidebar_content.o_display_view select[name="precision_day"] option[value="hour:quarter"]').prop('selected', true).trigger('change');
        await testUtils.nextTick();

    });

    QUnit.module('Map');

    QUnit.test('marker popup fields in editor sidebar', async function (assert) {
        // WOWL TODO
        assert.expect(12);
        let mapRenderer = null;
        patchWithCleanup(MapRenderer.prototype, {
            setup() {
                mapRenderer = this;
                this._super(...arguments);
            },
        });

        const partnerIds = pyEnv['res.partner'].search([['display_name', '=', 'Dustin']]);
        pyEnv['res.partner'].write(partnerIds, {
            display_name: 'Magan',
            partner_latitude: 10.0,
            partner_longitude: 10.5,
        });
        const irModelFieldsIds = pyEnv['ir.model.fields'].search([['name', 'in', ['name', 'description']]]);
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'mail.activity',
            arch: `<map res_partner='request_partner_id' routing='true' studio_map_field_ids='[${irModelFieldsIds[0]},${irModelFieldsIds[1]}]' hide_name='true' hide_address='true'>` +
                    "<field name='name' string='Name'/>" +
                    "<field name='summary' string='Description'/>" +
                "</map>",
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0], {
                        type: 'map_popup_fields',
                        target: {field_ids: [irModelFieldsIds[0]], operation_type: 'remove'},
                    });
                    const newArch = `<map res_partner='request_partner_id' routing='true' studio_map_field_ids='[${irModelFieldsIds[1]}]' hide_name='true' hide_address='true'>` +
                        "<field name='summary' string='Description'/>" +
                    "</map>";
                    return getCurrentMockServer()._mockReturnView(newArch, "mail.activity");
                }
            },
        });

        assert.containsOnce(vem, '.o_web_studio_sidebar .o_map_popup_fields',
            'Should have marker popup fields');
        assert.containsN(vem, '.o_web_studio_sidebar .o_map_popup_fields .badge', 2,
            'Should have two selected fields in marker popup fields');

        // Map rendered correctly
        assert.strictEqual(vem.view_type, 'map',
            'view type should be map');
        assert.strictEqual(mapRenderer.props.model.data.records.length, 1,
            'There should be one records');
        assert.containsOnce(vem.editor.el, 'div.leaflet-marker-icon',
            'There should be one marker on the map');

        // Marker popup have correct field
        await testUtils.dom.click($(vem.editor.el).find('div.leaflet-marker-icon'));

        assert.strictEqual($(vem.editor.el).find('.o-map-renderer--popup-table tbody tr:first .o-map-renderer--popup-table-content-name').text().trim(),
            'Name', 'Marker popup have should have a name field');
        assert.strictEqual($(vem.editor.el).find('.o-map-renderer--popup-table tbody tr:first .o-map-renderer--popup-table-content-value').text().trim(),
            'Chhagan', 'Marker popup have should have a name Chhagan');
        assert.strictEqual($(vem.editor.el).find('.o-map-renderer--popup-table tbody tr:last .o-map-renderer--popup-table-content-name').text().trim(),
            'Description', 'Marker popup have should have a Description field');
        assert.strictEqual($(vem.editor.el).find('.o-map-renderer--popup-table tbody tr:last .o-map-renderer--popup-table-content-value').text().trim(),
            'shaktiman', 'Marker popup have should have a description shaktiman');

        // Remove field and check marker popup fields
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_map_popup_fields .badge:first .o_delete'));
        assert.containsOnce(vem, '.o_web_studio_sidebar .o_map_popup_fields .badge',
            'Should have only one selected fields in marker popup fields');

        await testUtils.dom.click($(vem.editor.el).find('div.leaflet-marker-icon'));
        assert.containsOnce(vem.editor.el, '.o-map-renderer--popup-table tbody tr',
            'Marker popup have should have only Description field');
    });

    QUnit.module('Others');

    QUnit.test('error during tree rendering: undo', async function (assert) {
        assert.expect(4);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='id'/></tree>",
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    return getCurrentMockServer()._mockReturnView("<tree><field name='id'/></tree>", "coucou");
                }
            },
        });

        testUtils.mock.intercept(vem, 'studio_error', function (event) {
            assert.strictEqual(event.data.error, 'view_rendering',
                "should have raised an error");
        });


        // make the rendering crashes only the first time (the operation will
        // be undone and we will re-render with the old arch the second time)
        var oldRenderView = ListRenderer.prototype._renderView;
        var firstExecution = true;
        ListRenderer.prototype._renderView = function () {
            if (firstExecution) {
                firstExecution = false;
                throw "Error during rendering";
            } else {
                return oldRenderView.apply(this, arguments);
            }
        };

        // delete a field to generate a view edition
        await testUtils.dom.click(vem.$('.o_web_studio_list_view_editor [data-node-id]'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual($('.o_web_studio_view_renderer').length, 1,
            "there should only be one renderer");
        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "the view should be back as normal with 1 field");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_view',
            "the sidebar should have reset to its default mode");

        ListRenderer.prototype._renderView = oldRenderView;

    });

    QUnit.test('error in view edition: undo', async function (assert) {
        assert.expect(4);

        var firstExecution = true;
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='id'/></tree>",
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    if (firstExecution) {
                        firstExecution = false;
                        // simulate a failed route
                        return false;
                    } else {
                        return getCurrentMockServer()._mockReturnView("<tree><field name='id'/></tree>", "coucou");
                    }
                }
            },
        });

        testUtils.mock.intercept(vem, 'studio_error', function (event) {
            assert.strictEqual(event.data.error, 'wrong_xpath',
                "should have raised an error");
        });

        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be one field in the view");

        // delete a field to generate a view edition
        await testUtils.dom.click(vem.$('.o_web_studio_list_view_editor [data-node-id]'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        await testUtils.dom.click($('.modal-dialog .btn-primary'));

        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "the view should be back as normal with 1 field");
        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_view',
            "the sidebar should have reset to its default mode");

    });

    QUnit.test('add a monetary field without currency_id', async function (assert) {
        assert.expect(4);

        this.data.product.fields.monetary_field = {
            string: 'Monetary',
            type: 'monetary',
        };
        var arch = "<tree><field name='display_name'/></tree>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.deepEqual(args.operations[0].node.field_description, {
                        field_description: 'Currency',
                        model_name: 'coucou',
                        name: 'x_currency_id',
                        relation: 'res.currency',
                        type: 'many2one',
                    });
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        var currencyCreationText = "In order to use a monetary field, you need a currency field on the model. " +
            "Do you want to create a currency field first? You can make this field invisible afterwards.";

        // add a monetary field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_monetary'), vem.$('th.o_web_studio_hook').first());
        assert.strictEqual($('.modal-body:first').text(), currencyCreationText, "this should trigger an alert");
        await testUtils.dom.click($('.modal-footer .btn:contains(Cancel)'));

        // add a related monetary field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), vem.$('th.o_web_studio_hook').first());
        assert.strictEqual($('.modal .o_field_selector').length, 1,
            "a modal with a field selector should be opened to selected the related field");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2o]'));
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=monetary_field]'));
        await testUtils.dom.click($('.modal-footer .btn-primary:first'));
        assert.strictEqual($('.modal-body:eq(1)').text(), currencyCreationText, "this should trigger an alert");
        await testUtils.dom.click($('.modal-footer:eq(1) .btn:contains(Ok)'));

    });

    QUnit.test('add a monetary field with currency_id', async function (assert) {
        assert.expect(5);

        this.data.product.fields.monetary_field = {
            string: 'Monetary',
            type: 'monetary',
        };

        this.data.coucou.fields.x_currency_id = {
            string: "Currency",
            type: 'many2one',
            relation: "res.currency",
        };

        var arch = "<tree><field name='display_name'/></tree>";
        var nbEdit = 0;

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    nbEdit++;
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        // add a monetary field
        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be one node");
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_monetary'), $('.o_web_studio_hook'));
        assert.strictEqual(nbEdit, 1, "the view should have been updated");
        assert.strictEqual($('.modal').length, 0, "there should be no modal");

        // add a related monetary field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), vem.$('th.o_web_studio_hook').first());
        assert.strictEqual($('.modal .o_field_selector').length, 1,
            "a modal with a field selector should be opened to selected the related field");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2o]'));
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=monetary_field]'));
        await testUtils.dom.click($('.modal-footer .btn-primary:first'));
        assert.strictEqual(nbEdit, 2, "the view should have been updated");

    });

    QUnit.test('add a related field', async function (assert) {
        assert.expect(27);


        this.data.coucou.fields.related_field = {
            string: "Related",
            type: 'related',
        };
        this.data.product.fields.display_name.store = false;
        this.data.product.fields.m2o.store = true;

        var nbEdit = 0;
        const arch = "<tree><field name='display_name'/></tree>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    let newArch = arch;
                    if (nbEdit === 0) {
                        assert.strictEqual(args.operations[0].node.field_description.related,
                            'm2o.display_name', "related arg should be correct");
                        assert.strictEqual(args.operations[0].node.field_description.copy,
                            false, "copy arg should be correct");
                        assert.strictEqual(args.operations[0].node.field_description.readonly,
                            true, "readonly arg should be correct");
                        assert.strictEqual(args.operations[0].node.field_description.store,
                            false, "store arg should be correct");
                        newArch = "<tree><field name='display_name'/><field name='related_field'/></tree>";
                    } else if (nbEdit === 1) {
                        assert.strictEqual(args.operations[1].node.field_description.related,
                            'm2o.m2o', "related arg should be correct");
                        assert.strictEqual(args.operations[1].node.field_description.relation,
                            'partner', "relation arg should be correct for m2o");
                        assert.strictEqual(args.operations[0].node.field_description.copy,
                            false, "copy arg should be correct");
                        assert.strictEqual(args.operations[0].node.field_description.readonly,
                            true, "readonly arg should be correct");
                        assert.strictEqual(args.operations[1].node.field_description.store,
                            true, "store arg should be correct");
                    } else if (nbEdit === 2) {
                        assert.strictEqual(args.operations[2].node.field_description.related,
                            'm2o.partner_ids', "related arg should be correct");
                        assert.strictEqual(args.operations[2].node.field_description.relational_model,
                            'product', "relational model arg should be correct for o2m");
                        assert.strictEqual(args.operations[2].node.field_description.store,
                            false, "store arg should be correct");
                        assert.strictEqual(args.operations[0].node.field_description.copy,
                            false, "copy arg should be correct");
                        assert.strictEqual(args.operations[0].node.field_description.readonly,
                            true, "readonly arg should be correct");
                    } else if (nbEdit === 3) {
                        assert.strictEqual(args.operations[3].node.field_description.related,
                            'm2o.m2m', "related arg should be correct");
                        assert.strictEqual(args.operations[3].node.field_description.relation,
                            'product', "relational model arg should be correct for m2m");
                        assert.strictEqual(args.operations[3].node.field_description.store,
                            false, "store arg should be correct");
                    }
                    nbEdit++;
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });

        // listen to 'warning' events bubbling up
        testUtils.mock.intercept(vem, 'warning', assert.step.bind(assert, 'warning'));


        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), $('.o_web_studio_hook'));

        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");

        // try to create an empty related field
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.verifySteps(['warning'], "should have triggered a warning");
        assert.strictEqual($('.modal').length, 1, "the modal should still be displayed");

        $('.modal .o_field_selector').focusin(); // open the selector popover

        assert.containsOnce($, '.o_field_selector_popover li',
            "there should only be one available field (the many2one)");

        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2o]'));
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=display_name]'));
        await testUtils.dom.click($('.modal-footer .btn-primary:first'));


        // create a new many2one related field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2o]'));
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2o]'));
        await testUtils.dom.click($('.modal .o_field_selector .o_field_selector_close'));
        await testUtils.dom.click($('.modal-footer .btn-primary:first'));

        // create a new one2many related field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2o]'));
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=partner_ids]'));
        await testUtils.dom.click($('.modal .o_field_selector .o_field_selector_close'));
        await testUtils.dom.click($('.modal-footer .btn-primary:first'));

        // create a new many2many related field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_related'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");
        $('.modal .o_field_selector').focusin(); // open the selector popover
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2o]'));
        await testUtils.dom.click($('.o_field_selector_popover li[data-name=m2m]'));
        await testUtils.dom.click($('.modal .o_field_selector .o_field_selector_close')); // close the selector popover
        await testUtils.dom.click($('.modal-footer .btn-primary:first')); // confirm

        assert.strictEqual(nbEdit, 4, "should have edited the view");
        assert.verifySteps([], "should have triggered only one warning");

    });

    QUnit.test('add a one2many field', async function (assert) {
        assert.expect(8);

        var arch = '<form><group>' +
                        '<field name="display_name"/>' +
                    '</group></form>';
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    return Promise.resolve([
                        [1, 'Field 1'],
                        [2, 'Field 2'],
                    ]);
                }
                if (args.method === 'search_count' && args.model === 'ir.model.fields') {
                    assert.deepEqual(args.args, [[['relation', '=', 'coucou'], ['ttype', '=', 'many2one']]],
                        "the domain should be correctly set when checking if the m2o for o2m exists or not");
                }
                if (route === '/web_studio/edit_view') {
                    assert.step('edit');
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        // listen to 'warning' events bubbling up
        testUtils.mock.intercept(vem, 'warning', assert.step.bind(assert, 'warning'));

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_one2many'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");

        // try to confirm without specifying a related field
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.strictEqual($('.modal').length, 1, "the modal should still be displayed");
        assert.verifySteps(['warning'], "should have triggered a warning");

        // select a related field and confirm
        await testUtils.fields.many2one.clickOpenDropdown('field');
        await testUtils.fields.many2one.clickHighlightedItem('field');
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.verifySteps(['edit'], "should have created the field");

    });

    QUnit.test('add a one2many field without many2one', async function (assert) {
        assert.expect(3);

        var arch = '<form><group>' +
                        '<field name="display_name"/>' +
                    '</group></form>';
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'partner',
            arch: arch,
            mockRPC: function (route, args) {
                if (args.method === 'search_count' && args.model === 'ir.model.fields') {
                    assert.deepEqual(args.args, [[['relation', '=', 'partner'], ['ttype', '=', 'many2one']]],
                        "the domain should be correctly set when checking if the m2o for o2m exists or not");
                }
            },
        });

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_one2many'), $('.o_web_studio_hook'));
        assert.containsOnce($, '.modal main[role=alert]', "an alert modal should be displayed");
        await testUtils.dom.click($('.modal button:contains("Ok")'));
        assert.containsNone($, '.modal', "the modal should be closed");

    });

    QUnit.test('add a one2many lines field', async function (assert) {
        assert.expect(1);

        const arch = `
            <form>
                <group>
                    <field name="display_name"/>
                </group>
            </form>`;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'partner',
            arch: arch,
            mockRPC: function (route, args) {
                if (args.method === 'search_count') {
                    throw new Error('should not do a search_count');
                }
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.field_description.special, 'lines');
                    return getCurrentMockServer()._mockReturnView(arch, "partner");
                }
            },
        });

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_lines'), $('.o_web_studio_hook'));

    });

    QUnit.test('add a many2many field', async function(assert) {
        assert.expect(7);

        var arch = '<form><group>' +
                        '<field name="display_name"/>' +
                    '</group></form>';
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    return Promise.resolve([
                        [1, 'Model 1'],
                        [2, 'Model 2'],
                    ]);
                }
                if (route === '/web_studio/edit_view') {
                    assert.step('edit');
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        // listen to 'warning' events bubbling up
        testUtils.mock.intercept(vem, 'warning', assert.step.bind(assert, 'warning'));

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_many2many'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");

        // try to confirm without specifying a relation
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.strictEqual($('.modal').length, 1, "the modal should still be displayed");
        assert.verifySteps(['warning'], "should have triggered a warning");

        // select a model and confirm
        await testUtils.fields.many2one.clickOpenDropdown('model');
        await testUtils.fields.many2one.clickHighlightedItem('model');
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.verifySteps(['edit'], "should have created the field");

    });

    QUnit.test('add a many2one field', async function (assert) {
        assert.expect(7);

        var arch = '<form><group>' +
                        '<field name="display_name"/>' +
                    '</group></form>';
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    return Promise.resolve([
                        [1, 'Model 1'],
                        [2, 'Model 2'],
                    ]);
                }
                if (route === '/web_studio/edit_view') {
                    assert.step('edit');
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        // listen to 'warning' events bubbling up
        testUtils.mock.intercept(vem, 'warning', assert.step.bind(assert, 'warning'));

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_many2one'), $('.o_web_studio_hook'));
        assert.strictEqual($('.modal').length, 1, "a modal should be displayed");

        // try to confirm without specifying a relation
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.strictEqual($('.modal').length, 1, "the modal should still be displayed");
        assert.verifySteps(['warning'], "should have triggered a warning");

        // select a model and confirm
        await testUtils.fields.many2one.clickOpenDropdown('model');
        await testUtils.fields.many2one.clickHighlightedItem('model');
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.verifySteps(['edit'], "should have created the field");

    });

    QUnit.test('switch mode after element removal', async function (assert) {
        assert.expect(5);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='id'/><field name='display_name'/></tree>",
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    // the server sends the arch in string but it's post-processed
                    // by the ViewEditorManager
                    assert.ok(true, "should edit the view to delete the field");
                    const newArch = "<tree><field name='display_name'/></tree>";
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });

        assert.containsN(vem, '.o_web_studio_list_view_editor [data-node-id]', 2,
            "there should be two nodes");


        await testUtils.dom.click(vem.$('.o_web_studio_list_view_editor [data-node-id]:first'));

        assert.containsOnce(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should display the field properties");

        // delete a field
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be one node");
        assert.containsNone(vem, '.o_web_studio_sidebar_content.o_display_field',
            "the sidebar should have switched mode");

    });

    QUnit.test('open XML editor in read-only', async function (assert) {
        assert.expect(5);
        var done = assert.async();

        // the XML editor button is only available in debug mode
        var initialDebugMode = odoo.debug;
        odoo.debug = true;

        // the XML editor lazy loads its libs and its templates so its start
        // method is monkey-patched to know when the widget has started
        var XMLEditorDef = testUtils.makeTestPromise();
        testUtils.mock.patch(ace, {
            start: function () {
                return this._super.apply(this, arguments).then(function () {
                    XMLEditorDef.resolve();
                });
            },
        });

        var arch = "<form><sheet><field name='display_name'/></sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_editor/get_assets_editor_resources') {
                    assert.strictEqual(args.key, 1, "the correct view should be fetched");
                    return Promise.resolve({
                        views: [{
                            active: true,
                            arch: arch,
                            id: 1,
                            inherit_id: false,
                        }],
                        scss: [],
                        js: [],
                    });
                }
            },
            viewID: 1,
        });

        assert.containsOnce(vem, '.o_web_studio_view_renderer .o_form_readonly.o_web_studio_form_view_editor',
            "the form editor should be displayed");

        // open the XML editor
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar_header [name="view"]'));
        assert.containsOnce(vem, '.o_web_studio_sidebar .o_web_studio_xml_editor',
            "there should be a button to open the XML editor");
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_xml_editor'));

        assert.strictEqual(vem.$('.o_web_studio_view_renderer .o_form_readonly:not(.o_web_studio_form_view_editor)').length, 1,
            "the form should be in read-only");

        XMLEditorDef.then(function () {
            assert.containsOnce(vem, '.o_ace_view_editor', "the XML editor should be opened");

            // restore monkey-patched elements
            odoo.debug = initialDebugMode;
            testUtils.mock.unpatch(ace);

            done();
        });
    });

    QUnit.test('XML editor: reset operations stack', async function (assert) {
        assert.expect(6);
        var done = assert.async();

        // the XML editor button is only available in debug mode
        var initialDebugMode = odoo.debug;
        odoo.debug = true;

        // the XML editor lazy loads its libs and its templates so its start
        // method is monkey-patched to know when the widget has started
        var XMLEditorDef = testUtils.makeTestPromise();
        testUtils.mock.patch(ace, {
            start: function () {
                return this._super.apply(this, arguments).then(function () {
                    XMLEditorDef.resolve();
                });
            },
        });

        var arch = "<form><sheet><field name='display_name'/></sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                } else if (route === '/web_studio/edit_view_arch') {
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                } else if (route === '/web_editor/get_assets_editor_resources') {
                    assert.strictEqual(args.key, 1, "the correct view should be fetched");
                    return Promise.resolve({
                        views: [{
                            active: true,
                            arch: arch,
                            id: 1,
                            inherit_id: false,
                            name: "base view",
                        }, {
                            active: true,
                            arch: "<data/>",
                            id: 42,
                            inherit_id: 1,
                            name: "studio view",
                        }],
                        scss: [],
                        js: [],
                    });
                }
            },
            viewID: 1,
            studioViewID: 42,
        });
        assert.containsOnce(vem, '.o_web_studio_form_view_editor',
            "the form editor should be displayed");
        // do an operation
        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o_field_widget[name="display_name"]'));
        await testUtils.fields.editAndTrigger(vem.$('.o_web_studio_sidebar input[name="string"]'), 'Kikou', 'change');
        assert.strictEqual(vem.operations.length, 1,
            "there should be one operation in the stack (label rename)");

        // open the XML editor
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar_header [name="view"]'));
        assert.containsOnce(vem, '.o_web_studio_sidebar .o_web_studio_xml_editor',
            "there should be a button to open the XML editor");
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_xml_editor'));

        XMLEditorDef.then(async function () {
            assert.containsOnce(vem, '.o_ace_view_editor', "the XML editor should be opened");

            // the ace editor is too complicated to mimick so call the handler directly
            await vem.XMLEditor._saveView({
                id: 42,
                text: "<data></data>",
            });
            assert.strictEqual(vem.operations.length, 0,
                "the operation stack should be reset");

            // restore monkey-patched elements
            odoo.debug = initialDebugMode;
            testUtils.mock.unpatch(ace);

            done();
        });
    });

    QUnit.test('new button in buttonbox', async function (assert) {
        assert.expect(4);

        var arch = "<form><sheet><field name='display_name'/></sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
        });

        await testUtils.dom.click(vem.$('.o_web_studio_form_view_editor .o_web_studio_button_hook'));

        assert.strictEqual($('.modal:visible').length, 1, "there should be one modal");
        assert.strictEqual($('.o_web_studio_new_button_dialog').length, 1,
            "there should be a modal to create a button in the buttonbox");
        assert.strictEqual($('.o_web_studio_new_button_dialog .o_field_many2one').length, 1,
            "there should be a many2one for the related field");

        $('.o_web_studio_new_button_dialog .o_field_many2one input').focus();
        await testUtils.fields.editAndTrigger($('.o_web_studio_new_button_dialog .o_field_many2one input'), 'test', ['keyup', 'focusout']);

        assert.strictEqual($('.modal:visible').length, 1, "should not display the create modal");

    });

    QUnit.test('element removal', async function (assert) {
        assert.expect(10);

        var editViewCount = 0;
        var arch = "<form><sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                    "<field name='m2o'/>" +
                "</group>" +
                "<notebook><page name='page'><field name='id'/></page></notebook>" +
            "</sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    if (editViewCount === 1) {
                        assert.strictEqual(_.has(args.operations[0].target, 'xpath_info'), true,
                            'should give xpath_info even if we have the tag identifier attributes');
                    } else if (editViewCount === 2) {
                        assert.strictEqual(_.has(args.operations[1].target, 'xpath_info'), true,
                            'should give xpath_info even if we have the tag identifier attributes');
                    } else if (editViewCount === 3) {
                        assert.strictEqual(args.operations[2].target.tag, 'group',
                            'should compute correctly the parent node for the group');
                    } else if (editViewCount === 4) {
                        assert.strictEqual(args.operations[3].target.tag, 'notebook',
                            'should delete the notebook because the last page is deleted');
                        assert.strictEqual(_.last(args.operations[3].target.xpath_info).tag, 'notebook',
                            'should have the notebook as xpath last element');
                    }
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        // remove field
        await testUtils.dom.click(vem.$('[name="display_name"]').parent());
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        assert.strictEqual($('.modal-body:first').text(), "Are you sure you want to remove this field from the view?",
            "should display the correct message");
        await testUtils.dom.click($('.modal .btn-primary'));

        // remove other field so group is empty
        await testUtils.dom.click(vem.$('[name="m2o"]').parent());
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        assert.strictEqual($('.modal-body:first').text(), "Are you sure you want to remove this field from the view?",
            "should display the correct message");
        await testUtils.dom.click($('.modal .btn-primary'));

        // remove group
        await testUtils.dom.click(vem.$('.o_inner_group.o-web-studio-editor--element-clickable'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        assert.strictEqual($('.modal-body:first').text(), "Are you sure you want to remove this group from the view?",
            "should display the correct message");
        await testUtils.dom.click($('.modal .btn-primary'));

        // remove page
        await testUtils.dom.click(vem.$('.o_notebook li.o-web-studio-editor--element-clickable'));
        await testUtils.dom.click(vem.$('.o_web_studio_sidebar .o_web_studio_remove'));
        assert.strictEqual($('.modal-body:first').text(), "Are you sure you want to remove this page from the view?",
            "should display the correct message");
        await testUtils.dom.click($('.modal .btn-primary'));

        assert.strictEqual(editViewCount, 4,
            "should have edit the view 4 times");
    });

    QUnit.test('update sidebar after edition', async function (assert) {
        assert.expect(5);

        var editViewCount = 0;
        var arch = "<form><sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                "</group>" +
                "<notebook><page><field name='id'/></page></notebook>" +
            "</sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        // rename field
        await testUtils.dom.click(vem.$('[name="display_name"]').parent());

        assert.containsOnce(vem.el, '.o_wrap_label.o-web-studio-editor--element-clicked[data-field-name=display_name]');
        assert.strictEqual(vem.el.querySelector(".o_web_studio_sidebar [name=string]").value, "Display Name");
        vem.$('.o_web_studio_sidebar [name="string"]').focus();
        await testUtils.fields.editAndTrigger(vem.$('.o_web_studio_sidebar [name="string"]'), 'test', 'change');
        assert.containsOnce(vem.el, '.o_wrap_label.o-web-studio-editor--element-clicked[data-field-name=display_name]');
        // The name stay the same because on the mockRPC we return the same view.
        assert.strictEqual(vem.el.querySelector(".o_web_studio_sidebar [name=string]").value, "Display Name");

        assert.strictEqual(editViewCount, 1,
            "should have edit the view 1 time");

    });

    QUnit.test('default value in sidebar', async function (assert) {
        assert.expect(2);

        var arch = "<form><sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                    "<field name='priority'/>" +
                "</group>" +
            "</sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/get_default_value') {
                    if (args.field_name === 'display_name') {
                        return Promise.resolve({default_value: 'yolo'});
                    } else if (args.field_name === 'priority') {
                        return Promise.resolve({default_value: '1'});
                    }
                }
            },
        });

        await testUtils.dom.click(vem.$('[name="display_name"]').parent());
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field input[data-type="default_value"]').val(), "yolo",
            "the sidebar should now display the field properties");

        await testUtils.dom.click(vem.$('[name="priority"]').parent());
        assert.strictEqual(vem.$('.o_web_studio_sidebar_content.o_display_field select[data-type="default_value"]').val(), "1",
            "the sidebar should now display the field properties");

    });

    QUnit.test('default value for new field name', async function (assert) {
        assert.expect(2);

        let editViewCount = 0;
        const arch = `<form><sheet>
            <group>
            <field name='display_name'/>
            </group>
            </sheet></form>`;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                    // new field default name should be x_studio_[FieldType]_field_[RandomString]
                    if (editViewCount === 1) {
                        assert.ok(args.operations[0].node.field_description.name.startsWith('x_studio_char_field_'),
                            "default new field name should start with x_studio_char_field_*");
                    } else if (editViewCount === 2) {
                        assert.ok(args.operations[1].node.field_description.name.startsWith('x_studio_float_field_'),
                            "default new field name should start with x_studio_float_field_*");
                    }
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_char'), vem.$('.o_inner_group .o_web_studio_hook:first'));
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_float'), vem.$('.o_inner_group .o_web_studio_hook:first'));

    });

    QUnit.test('remove starting underscore from new field value', async function (assert) {
        assert.expect(1);
        // renaming is only available in debug mode
        patchWithCleanup(odoo, { debug: true });

        const self = this;
        const arch = `<form><sheet>
            <group>
            <field name="display_name"/>
            </group>
            </sheet></form>`;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    const fieldName = args.operations[0].node.field_description.name;
                    const newArch = `<form><sheet><group><field name='${fieldName}'/><field name='display_name'/></group></sheet></form>`;
                    self.data.coucou.fields[fieldName] = {
                        string: "Hello",
                        type: "char"
                    };
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                } else if (route === '/web_studio/rename_field') {
                    // random value returned in order for the mock server to know that this route is implemented.
                    return true;
                }
            },
        });

        await testUtils.dom.dragAndDrop(vem.el.querySelector('.o_web_studio_new_fields .o_web_studio_field_char'), vem.$('.o_inner_group .o_web_studio_hook:first'));

        // rename the field
        await testUtils.fields.editAndTrigger(vem.el.querySelector('.o_web_studio_sidebar input[name="name"]'), '__new', ['change']);
        assert.strictEqual(vem.el.querySelector('.input-group input').value, 'new', "value should not contain starting underscore in new field");
    });

    QUnit.test('notebook and group not drag and drop in a group', async function (assert) {
        assert.expect(2);
        var editViewCount = 0;
        var arch = "<form><sheet>" +
                "<group>" +
                    "<group>" +
                        "<field name='display_name'/>" +
                    "</group>" +
                    "<group>" +
                    "</group>" +
                "</group>" +
            "</sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    editViewCount++;
                }
            },
        });
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_tabs'), $('.o_group .o_web_studio_hook'));
        assert.strictEqual(editViewCount, 0,
            "the notebook cannot be dropped inside a group");
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_columns'), $('.o_group .o_web_studio_hook'));
        assert.strictEqual(editViewCount, 0,
            "the group cannot be dropped inside a group");
    });

    QUnit.test('drop monetary field outside of group', async function (assert) {
        assert.expect(1);

        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<form><sheet/></form>",
        });

        await testUtils.dom.dragAndDrop(
            vem.$('.o_web_studio_new_fields .o_web_studio_field_monetary'),
            $('.o_web_studio_hook'),
            { disableDrop: true }
        );
        assert.containsNone(vem, '.o_web_studio_nearest_hook', "There should be no highlighted hook");
    });

    QUnit.test('add a selection field in non debug', async function (assert) {
        assert.expect(14);

        // inline selection edition is only available in non debug mode
        var initialDebugMode = odoo.debug;
        odoo.debug = false;
        var arch = "<tree><field name='display_name'/></tree>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.field_description.selection,
                        "[[\"Value 1\",\"Miramar\"]]",
                        "the selection value should be set correctly");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });

        testUtils.mock.intercept(vem, 'warning', assert.step.bind(assert, 'warning'), true);

        await testUtils.dom.dragAndDrop(
            vem.$('.o_web_studio_new_fields .o_web_studio_field_selection'),
            vem.$('.o_web_studio_hook:first'));
        assert.containsOnce($, '.modal .o_web_studio_field_dialog_form',
            "a modal should be opened");
        assert.containsNone($, '.modal .o_web_studio_selection_editor',
            "there should be no selection editor");

        // saving selection with no values should show a warning and not save
        assert.containsNone($, '.modal .o_web_studio_selection_editor > li',
            "there should be 0 selection value");
        assert.verifySteps([]);  // making sure no warning was triggered before clicking on Confirm
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.verifySteps(["warning"]);  // make sure a warning was triggered
        assert.containsNone($, '.modal .o_web_studio_selection_editor > li',
            "there should still be 0 selection value")
        assert.containsOnce($, '.modal .o_web_studio_field_dialog_form',
            "a modal should still be opened");

        // add a new value (with ENTER)
        await testUtils.fields.editAndTrigger($('.modal .o_web_studio_selection_new_value input'),
            'Value 1', [$.Event('keyup', { which: $.ui.keyCode.ENTER })]);
        assert.containsOnce($, '.modal .o_web_studio_selection_editor > li',
            "there should be 1 selection value");
        assert.containsOnce($, '.modal .o_web_studio_selection_editor > li span:contains(Value 1)',
            "the value should be correctly set");

        // edit the first value
        await testUtils.dom.click($('.modal .o_web_studio_selection_editor li:first .o_web_studio_edit_selection_value'));
        assert.containsOnce($, '.modal',
            "new modal to edit selection value should not open in non debug mode");
        assert.strictEqual($('.modal .o_web_studio_selection_editor li:first').find('.o_web_studio_selection_input').val(), "Value 1",
            "the value should be set in the input in li");

        await testUtils.fields.editAndTrigger($('.modal .o_web_studio_selection_editor li:first .o_web_studio_selection_input'),
            'Miramar', ['blur']);
        assert.containsOnce($, '.modal .o_web_studio_selection_editor > li:first span:contains(Miramar)',
            "the value should have been updated");

         // Click 'Confirm' button for the new field dialog
        await testUtils.dom.click($('.modal button:contains("Confirm")'));

        odoo.debug = initialDebugMode;
    });

    QUnit.test('add a selection field in debug', async function (assert) {
        assert.expect(20);

        // Dialog to edit selection values is only available in debug mode
        var initialDebugMode = odoo.debug;
        odoo.debug = true;
        var arch = "<tree><field name='display_name'/></tree>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.field_description.selection,
                        "[[\"Value 2\",\"Value 2\"],[\"Value 1\",\"My Value\"],[\"Sulochan\",\"Sulochan\"]]",
                        "the selection should be set");
                    assert.ok(true, "should have refreshed the view");
                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        testUtils.mock.intercept(vem, 'warning', assert.step.bind(assert, 'warning'), true);

        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_selection'), $('.o_web_studio_hook:first'));
        assert.strictEqual($('.modal .o_web_studio_field_dialog_form').length, 1, "a modal should be opened");
        assert.strictEqual($('.modal .o_web_studio_selection_editor').length, 0, "there should be no selection editor");

        // saving selection with no values should show a warning and not save
        assert.containsNone($, '.modal .o_web_studio_selection_editor > li',
            "there should be 0 selection value");
        assert.verifySteps([]);  // making sure no warning was triggered before clicking on Confirm
        await testUtils.dom.click($('.modal button:contains("Confirm")'));
        assert.verifySteps(["warning"]);  // make sure a warning was triggered
        assert.containsNone($, '.modal .o_web_studio_selection_editor > li',
            "there should still be 0 selection value")
        assert.containsOnce($, '.modal .o_web_studio_field_dialog_form',
            "a modal should still be opened");

        // add a new value (with ENTER)
        $('.modal .o_web_studio_selection_new_value input')
            .val('Value 1')
            .trigger($.Event('keyup', {which: $.ui.keyCode.ENTER}));
        await testUtils.nextTick();
        assert.strictEqual($('.modal .o_web_studio_selection_editor > li').length, 1, "there should be 1 selection value");
        assert.strictEqual($('.modal .o_web_studio_selection_editor > li span:contains(Value 1)').length, 1, "the value should be correctly set");

        // add a new value (with button 'fa-check' )
        $('.modal .o_web_studio_selection_new_value input').val('Value 2');
        await testUtils.dom.click($('.modal .o_web_studio_add_selection_value'));
        assert.strictEqual($('.modal .o_web_studio_selection_editor > li').length, 2, "there should be 2 selection values");

        // edit the first value
        await testUtils.dom.click($('.modal .o_web_studio_selection_editor li:first .o_web_studio_edit_selection_value'));
        assert.strictEqual($('.modal').length, 2, "a new modal should be opened");
        assert.strictEqual($('.modal:eq(1) input#o_selection_label').val(), "Value 1",
            "the value should be set in the edition modal");
        $('.modal:eq(1) input#o_selection_label').val('My Value');
        await testUtils.dom.click($('.modal:eq(1) button:contains(Confirm)'));
        assert.strictEqual($('.modal').length, 1, "the second modal should be closed");
        assert.strictEqual($('.modal .o_web_studio_selection_editor > li:first span:contains(My Value)').length, 1, "the value should have been updated");

        // add a value and delete it
        $('.modal .o_web_studio_selection_new_value input').val('Value 3');
        await testUtils.dom.click($('.modal .o_web_studio_add_selection_value'));
        assert.strictEqual($('.modal .o_web_studio_selection_editor > li').length, 3, "there should be 3 selection values");

        await testUtils.dom.click($('.modal .o_web_studio_selection_editor > li:eq(2) .o_web_studio_remove_selection_value'));

        assert.strictEqual($('.modal .o_web_studio_selection_editor > li').length, 2, "there should be 2 selection values");

        // reorder values
        await testUtils.dom.dragAndDrop(
            $('.modal .ui-sortable-handle').eq(1),
            $('.modal .o_web_studio_selection_editor > li').first(),
            {position: 'top'});
        assert.strictEqual($('.modal .o_web_studio_selection_editor > li:first span:contains(Value 2)').length, 1, "the values should have been reordered");

        // Verify that on confirm, new value is added without button 'fa-check' or 'ENTER'
        $('.modal .o_web_studio_selection_new_value input')
            .val('Sulochan');
        await testUtils.dom.click($('.modal button:contains(Confirm)'));

        odoo.debug = initialDebugMode;
    });

    QUnit.test('add a selection field with widget priority', async function (assert) {
        assert.expect(5);

        var arch = "<tree><field name='display_name'/></tree>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.strictEqual(args.operations[0].node.field_description.type, "selection",
                        "the type should be correctly set");
                    assert.deepEqual(args.operations[0].node.field_description.selection, [['0','Normal'], ['1','Low'], ['2','High'], ['3','Very High']],
                        "the selection should be correctly set");
                    assert.strictEqual(args.operations[0].node.attrs.widget, "priority",
                        "the widget should be correctly set");

                    return getCurrentMockServer()._mockReturnView(arch, "coucou");
                }
            },
        });


        assert.containsOnce(vem, '.o_web_studio_list_view_editor [data-node-id]',
            "there should be one node");
        // add a priority field
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_priority'), $('.o_web_studio_hook'));

        assert.strictEqual($('.modal').length, 0, "there should be no modal");

    });

    QUnit.test('blockUI not removed just after rename', async function (assert) {
        assert.expect(15);
        // renaming is only available in debug mode
        var initialDebugMode = odoo.debug;
        odoo.debug = true;

        var blockUI = framework.blockUI;
        var unblockUI = framework.unblockUI;
        framework.blockUI = function () {
            assert.step('block UI');
        };
        framework.unblockUI = function () {
            assert.step('unblock UI');
        };

        const self = this;
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: "<tree><field name='display_name'/></tree>",
            mockRPC: function(route, args) {
                if (!['/mail/init_messaging', '/mail/load_message_failures', '/bus/im_status', ...ROUTES_TO_IGNORE].includes(route)) {
                    assert.step(route);
                }
                if (route === '/web_studio/edit_view') {
                    var fieldName = args.operations[0].node.field_description.name;
                    const newArch = `<tree><field name='${fieldName}'/><field name='display_name'/></tree>`;
                    self.data.coucou.fields[fieldName] = {
                        string: "Coucou",
                        type: "char"
                    };
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                } else if (route === '/web_studio/rename_field') {
                    // random value returned in order for the mock server to know that this route is implemented.
                    return true;
                }
            }
        });

        assert.strictEqual(vem.$('thead th[data-node-id]').length, 1, "there should be one field");

        // create a new field before existing one
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_char'), vem.$('.o_web_studio_hook:first'));
        await testUtils.nextTick();
        assert.strictEqual(vem.$('thead th[data-node-id]').length, 2, "there should be two fields");

        // rename the field
        await testUtils.fields.editAndTrigger(vem.$('.o_web_studio_sidebar input[name="name"]'), 'new', ['change']);

        assert.verifySteps([
            '/web/dataset/search_read',
            'block UI',
            '/web_studio/edit_view',
            '/web/dataset/search_read',
            'unblock UI',
            '/web_studio/get_default_value',
            'block UI',
            '/web_studio/rename_field',
            '/web_studio/edit_view',
            '/web/dataset/search_read',
            '/web_studio/get_default_value',
            'unblock UI',
        ]);


        framework.blockUI = blockUI;
        framework.unblockUI = unblockUI;
        odoo.debug = initialDebugMode;
    });

    QUnit.test('blockUI not removed just after field dropped', async function (assert) {
        assert.expect(6);

        const blockUI = framework.blockUI;
        const unblockUI = framework.unblockUI;
        framework.blockUI = function () {
            assert.step('block UI');
        };
        framework.unblockUI = function () {
            assert.step('unblock UI');
        };

        const arch = "<tree><field name='display_name'/></tree>";
        const self = this;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.step(route);
                    const fieldName = args.operations[0].node.field_description.name;
                    const newArch = `<tree><field name='${fieldName}'/><field name='display_name'/></tree>`;
                    self.data.coucou.fields[fieldName] = {
                        string: "Coucou",
                        type: "char"
                    };
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            }
        });

        assert.strictEqual(vem.$('thead th[data-node-id]').length, 1, "there should be one field");

        // create a new field before existing one
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_new_fields .o_web_studio_field_char'), vem.$('.o_web_studio_hook:first'));
        await testUtils.nextTick();
        assert.strictEqual(vem.$('thead th[data-node-id]').length, 2, "there should be two fields");

        assert.verifySteps([
            'block UI',
            '/web_studio/edit_view',
            'unblock UI',
        ]);


        framework.blockUI = blockUI;
        framework.unblockUI = unblockUI;
    });

    // kanbanSkip('Find tag in simple view', async function (assert) {
    //     assert.expect(2);
    //     const arch = `
    //         <form>
    //             <field name='display_name'/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     let node = vem.editor.findNode(vem.view.arch, {tag: 'field'});
    //     assert.equal(node.tag, 'field', "It shoudl have found the node");
    //     node = vem.editor.findNode(vem.view.arch, {tag: 'field', attrs: {class: 'not-in-dom'}});
    //     assert.notOk(node, "It should not have found anything")
    // });

    // kanbanSkip('Find with other class', async function (assert) {
    //     assert.expect(1);
    //     const arch = `
    //         <form>
    //             <field class="my-class other-class" name='display_name'/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     let node = vem.editor.findNode(vem.view.arch, {tag: 'field', class: 'my-class'});
    //     assert.equal(node.tag, 'field', "It shoudl have found the node");
    // });

    // kanbanSkip('Find tag and attr in simple view', async function (assert) {
    //     assert.expect(3);
    //     const arch = `
    //         <form>
    //             <field class='my-class' name='display_name'/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     let node = vem.editor.findNode(vem.view.arch, {tag: 'field', class: 'my-class'});
    //     assert.equal(node.tag, 'field', "It should have found the node");
    //     assert.equal(node.attrs.class, 'my-class', "It should have found the node");
    //     node = vem.editor.findNode(vem.view.arch, {tag: 'field', class: 'other-class'});
    //     assert.notOk(node, "It should not have found anything")
    // });

    // kanbanSkip('Find first tag', async function (assert) {
    //     assert.expect(1);
    //     const arch = `
    //         <form>
    //             <field class='my-class' name='display_name'/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     const node = vem.editor.findNode(vem.view.arch, {tag: 'form'});
    //     assert.equal(node.tag, 'form', "It should have found the node");
    // });

    // kanbanSkip('Find first neigbours', async function (assert) {
    //     assert.expect(2);
    //     const arch = `
    //         <form>
    //             <field name='display_name' class="first"/>
    //             <field name='start' class="second"/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     const node = vem.editor.findNode(vem.view.arch, {tag: 'field'});
    //     assert.equal(node.tag, 'field', "It should have found the node");
    //     assert.equal(node.attrs.class, 'first', "It should have found the first node");
    // });

    // kanbanSkip('Find nested node', async function (assert) {
    //     assert.expect(2);
    //     const arch = `
    //         <form>
    //             <group>
    //                 <group>
    //                     <field name='display_name' class="nested"/>
    //                 </group>
    //             </group>
    //             <group>
    //                 <field name='start' class="not-nested"/>
    //             </group>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     const node = vem.editor.findNode(vem.view.arch, {tag: 'field'});
    //     assert.equal(node.tag, 'field', "It should have found the node");
    //     assert.equal(node.attrs.class, 'not-nested', "It should have found the first node");
    // });

    // kanbanSkip('Find invisble', async function (assert) {
    //     assert.expect(2);
    //     const arch = `
    //         <form>
    //             <field name='display_name' invisible="0"/>
    //             <field name='start' invisible="1"/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     const node = vem.editor.findNode(vem.view.arch, {tag: 'field', invisible: "1"});
    //     assert.equal(node.tag, 'field', "It should have found the node");
    //     assert.equal(node.attrs.name, 'start', "It should have found the invisible node");
    // });

    // kanbanSkip('Find node with attr only', async function (assert) {
    //     assert.expect(1);
    //     const arch = `
    //         <form>
    //             <field name='display_name'/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     const node = vem.editor.findNode(vem.view.arch, {name: 'display_name'});
    //     assert.equal(node.tag, 'field', "It should have found the node");
    // });

    // kanbanSkip('Find node with multiple attrs', async function (assert) {
    //     assert.expect(2);
    //     const arch = `
    //         <form>
    //             <field name='display_name' class="my-class"/>
    //         </form>
    //     `
    //     const vem = await studioTestUtils.createViewEditorManager({
    //         model: 'coucou',
    //         arch: arch,
    //     });
    //     let node = vem.editor.findNode(vem.view.arch, {
    //         class: "not-my-class",
    //         name: 'display_name',
    //     });
    //     assert.notOk(node, "It should not have matched the node")
    //     node = vem.editor.findNode(vem.view.arch, {
    //         class: "my-class",
    //         name: 'display_name',
    //     });
    //     assert.equal(node.tag, 'field', "It should have matched the node");
    // });

    QUnit.test("Sidebar should display all field's widgets", async function (assert) {
        assert.expect(5);

        const arch = `
            <form><sheet>
                <group>
                    <field name="display_name"/>
                </group>
            </sheet></form>`;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
        });

        await testUtils.dom.click(vem.$('.o_field_widget'));

        const displayedWidgetNames = Array
            .from(document.getElementById('widget')
            .options).map(x => x.label);

        const charWidgetNames = [
            "Copy to Clipboard",
            "Email",
            "Phone",
            "Text",
            "URL"
        ];
        for (const name of charWidgetNames) {
            assert.ok(displayedWidgetNames.includes(name));
        }

    });

    QUnit.test("Sidebar should display component field's widgets", async function (assert) {
        assert.expect(1);

        class CompField extends AbstractFieldOwl {}
        CompField.template = xml`<div></div>`;
        CompField.description = 'Component Field';
        CompField.supportedFieldTypes = ['char'];

        fieldRegistryOwl.add('comp_field', CompField);

        const arch = `
            <form><sheet>
                <group>
                    <field name="display_name"/>
                </group>
            </sheet></form>`;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
        });

        await testUtils.dom.click(vem.$('.o_field_widget'));

        const displayedWidgetNames = Array
            .from(document.getElementById('widget')
            .options).map(x => x.label);

        assert.ok(displayedWidgetNames.includes(CompField.description));

        delete fieldRegistryOwl.map.comp_field;

    });

    QUnit.test('click on the "More" Button', async function (assert) {
        assert.expect(2);

        // the 'More' button is only available in debug mode
        patchWithCleanup(odoo, { debug: true });

        const action = serverData.actions["studio.coucou_action"];
        const irUiViewId1 = pyEnv['ir.ui.view'].create({ model: 'bloups' });
        action.views = [[irUiViewId1, "form"]];
        action.res_model = "coucou";
        serverData.views[`coucou,${irUiViewId1},form`] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <tree><field name='display_name'/></tree>
                    </field>
                </sheet>
            </form>`;
        serverData.views["coucou,false,search"] = `<search></search>`;

        serverData.views["ir.ui.view,false,form"] = /*xml */ `<form><field name="model" /></form>`;
        serverData.views["ir.ui.view,false,search"] = /*xml */ `<search />`;

        const webClient = await createEnterpriseWebClient({ serverData, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);
        await testUtils.dom.click(target.querySelector(".o_web_studio_view"));

        assert.containsOnce(target, '.o_web_studio_sidebar .o_web_studio_parameters',
            "there should be the button to go to the ir.ui.view form");
        await testUtils.dom.click(target.querySelector('.o_web_studio_sidebar .o_web_studio_parameters'));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_studio .o_action_manager .o_form_view");
    });

    QUnit.module('X2Many');

    QUnit.test('edit one2many form view (2 level) and check that the correct model is passed', async function (assert) {
        assert.expect(1);

        patchWithCleanup(framework, {
            blockUI: () => Promise.resolve(),
            unblockUI: () => Promise.resolve()
        });

        const coucouId1 = pyEnv['coucou'].create({
            display_name: 'Coucou 11',
            product_ids: pyEnv['product'].search([['display_name', '=', 'xpad']]),
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = coucouId1;
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name="display_name"/>
                    <field name="product_ids">
                        <form>
                            <sheet>
                                <field name="m2m" widget='many2many_tags'/>
                            </sheet>
                        </form>
                    </field>
                </sheet>
            </form>`;

        Object.assign(serverData.views, {
            "product,2,list": "<tree><field name='display_name'/></tree>",
            "partner,3,list": "<tree><field name='display_name'/></tree>",
        });


        patchWithCleanup(MockServer.prototype, {
            mockEditView(args) {
                assert.equal(args.model, "product")
                return this._super(...arguments);
            }
        });

        const webClient = await createEnterpriseWebClient({ serverData, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // edit the x2m form view
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_one2many'));
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'));
        await legacyExtraNextTick();
        await testUtils.dom.click($(target).find('.o_field_many2many_tags'));
        await testUtils.dom.click($(target).find('#option_no_create'));
    });

    QUnit.test('disable creation(no_create options) in many2many_tags widget', async function (assert) {
        assert.expect(3);

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "product";
        serverData.views["product,1,form"] = /*xml*/`
            <form>
                <sheet>
                    <group>
                        <field name='display_name'/>
                        <field name='m2m' widget='many2many_tags'/>
                    </group>
                </sheet>
            </form>`;
        serverData.views["product,false,search"] = `<search></search>`;

        const mockRPC = (route, args) => {
            if (route === '/web_studio/edit_view') {
                assert.equal(args.operations[0].new_attrs.options, '{"no_create":true}',
                    'no_create options should send with true value');
            }
        }

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer .o_field_many2many_tags'));
        assert.containsOnce(target, '.o_web_studio_sidebar #option_no_create',
            "should have no_create option for m2m field");
        assert.notOk($(target).find('.o_web_studio_sidebar #option_no_create').is(':checked'),
            'by default the no_create option should be false');

        await testUtils.dom.click($(target).find('.o_web_studio_sidebar #option_no_create'));
    });

    QUnit.test('disable creation(no_create options) in many2many_tags_avatar widget', async function (assert) {
        assert.expect(3);

        const arch = `
            <form>
                <sheet>
                    <field name="m2m" widget="many2many_tags_avatar"/>
                </sheet>
            </form>`;
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'product',
            arch,
            mockRPC: function (route, args) {
                if (route === '/web_studio/edit_view') {
                    assert.equal(args.operations[0].new_attrs.options, '{"no_create":true}',
                        'no_create options should send with true value');
                    return getCurrentMockServer()._mockReturnView(arch, "product");
                }
            },
        });

        await testUtils.dom.click(vem.$('.o_web_studio_view_renderer .o_field_many2many_tags_avatar'));
        assert.containsOnce(vem, '.o_web_studio_sidebar #option_no_create',
            "should have no_create option for many2many_tags_avatar widget");
        assert.notOk(vem.$('.o_web_studio_sidebar #option_no_create').is(':checked'),
            'by default the no_create option should be false');

        await testUtils.dom.click(vem.$('.o_web_studio_sidebar #option_no_create'));

    });

    QUnit.test('disable creation(no_create options) in many2many_avatar_user and many2many_avatar_employee widget', async function (assert) {
        assert.expect(3);

        serverData.models.product.fields.m2m_users = {
            string: "M2M Users",
            type: 'many2many',
            relation: "res.users",
        };
        serverData.models.product.fields.m2m_employees = {
            string: "M2M Employees",
            type: 'many2many',
            relation: "hr.employee.public",
        };

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "product";
        serverData.views["product,1,form"] = /*xml*/ `
            <form>
                <sheet>
                    <field name="m2m_users" widget="many2many_avatar_user"/>
                </sheet>
            </form>`;
        serverData.views["product,false,search"] = `<search></search>`;

        const mockRPC = (route, args) => {
            if (route === '/web_studio/edit_view') {
                assert.equal(args.operations[0].new_attrs.options, '{"no_create":true}',
                    'no_create options should send with true value');
            }
        }
        // Required by widget.
        registry.category("services").add("messaging", {
            start() {
                return {
                    get: async() => {return {}},
                    modelManager: {
                        startListening: () => {},
                        stopListening: () => {},
                        removeListener: () => {},
                        messagingCreatedPromise: testUtils.makeTestPromise(),
                    },
                };
            }
        });
        const webClient = await createEnterpriseWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // check many2many_avatar_user
        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer .o_field_many2many_avatar_user[name="m2m_users"]'));
        assert.containsOnce(target, '.o_web_studio_sidebar #option_no_create',
            "should have no_create option for many2many_avatar_user");
        assert.notOk($(target).find('.o_web_studio_sidebar #option_no_create').is(':checked'),
            'by default the no_create option should be false');

        await testUtils.dom.click($(target).find('.o_web_studio_sidebar #option_no_create'));
    });

    QUnit.test('display one2many without inline views', async function (assert) {
        assert.expect(6);

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids' widget="one2many"/>
                </sheet>
            </form>`;
        serverData.views["coucou,false,search"] = `<search></search>`;
        serverData.views["product,2,list"] = `<tree><field name="toughness"/></tree>`;

        const mockRPC = (route, args) => {
            if (route === "/web_studio/create_inline_view") {
                const { model, field_name, subview_type, subview_xpath, view_id } = args;
                assert.strictEqual(model, "product");
                assert.strictEqual(field_name, "product_ids");
                assert.strictEqual(subview_type, "tree");
                assert.strictEqual(subview_xpath, "");
                assert.strictEqual(view_id, 1);

                // hardcode inheritance mechanisme
                serverData.views["coucou,1,form"] = /*xml */ `
                    <form>
                        <sheet>
                            <field name='display_name'/>
                            <field name='product_ids'>${serverData.views["product,2,list"]}</field>
                        </sheet>
                    </form>`;
                return serverData.views["product,2,list"];
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        var $one2many = $(target).find('.o_field_one2many.o_field_widget');
        assert.strictEqual($one2many.children().length, 1,
            "The one2many widget should be displayed");

        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer .o_field_one2many'));
        await testUtils.dom.click(
            $(target).find('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="list"]'));
        await legacyExtraNextTick();
    });

    QUnit.test('edit one2many list view', async function (assert) {
        assert.expect(17);

        patchWithCleanup(framework, {
            blockUI: () => Promise.resolve(),
            unblockUI: () => Promise.resolve()
        });

        // the 'More' button is only available in debug mode
        patchWithCleanup(odoo, { debug: true });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <tree><field name='display_name'/></tree>
                    </field>
                </sheet>
            </form>`;
        serverData.views["coucou,false,search"] = `<search></search>`;

        const mockRPC = (route, args) => {
            if (route === '/web_studio/get_default_value') {
                assert.step(args.model_name);
                return Promise.resolve({});
            }
            if (args.method === 'search_read' && args.model === 'ir.model.fields') {
                assert.deepEqual(args.kwargs.domain, [['model', '=', 'product'], ['name', '=', 'coucou_id']],
                    "the model should be correctly set when editing field properties");
                return Promise.resolve([]);
            }
            if (route === '/web_studio/edit_view') {
                assert.strictEqual(args.view_id, 1);
                assert.strictEqual(args.operations.length, 1);

                const operation = args.operations[0];
                assert.strictEqual(operation.type, "add");
                assert.strictEqual(operation.position, "before");

                assert.deepEqual(operation.node, {
                    tag: "field",
                    attrs: {
                        name: "coucou_id",
                        optional: "show",
                    }
                });

                const target = operation.target;
                assert.deepEqual(target.attrs, {name: "display_name"});
                assert.strictEqual(target.tag, "field");
                assert.strictEqual(target.subview_xpath, "//field[@name='product_ids']/tree");

                serverData.views["coucou,1,form"] = /*xml */ `
                    <form>
                        <sheet>
                            <field name='display_name'/>
                            <field name='product_ids'>
                                <tree><field name='coucou_id'/><field name='display_name'/></tree>
                            </field>
                        </sheet>
                    </form>`;
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer .o_field_one2many'));
        const blockOverlayZindex = target.querySelector('.o_web_studio_view_renderer .o_field_one2many .o-web-studio-edit-x2manys-buttons').style['z-index'];
        assert.strictEqual(blockOverlayZindex, '1000',
            "z-index of blockOverlay should be 1000");
        assert.verifySteps(['coucou']);

        await testUtils.dom.click($($(target).find('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many')[0]));
        await legacyExtraNextTick();
        assert.containsOnce(target, '.o_web_studio_view_renderer thead tr [data-node-id]',
            "there should be 1 nodes in the x2m editor.");

        await testUtils.dom.dragAndDrop($(target).find('.o_web_studio_existing_fields .o_web_studio_field_many2one')[0], $('.o_web_studio_hook'));
        await testUtils.nextTick();

        assert.containsN(target, '.o_web_studio_view_renderer thead tr [data-node-id]', 2,
            "there should be 2 nodes after the drag and drop.");

        // click on a field in the x2m list view
        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer [data-node-id]:first'));
        await legacyExtraNextTick();
        assert.verifySteps(['product'], "the model should be the x2m relation");

        // edit field properties
        assert.containsOnce(target, '.o_web_studio_sidebar .o_web_studio_parameters',
            "there should be button to edit the field properties");
        await testUtils.dom.click($(target).find('.o_web_studio_sidebar .o_web_studio_parameters'));
    });

    QUnit.test('edit one2many list view with tree_view_ref context key', async function (assert) {
        assert.expect(6);

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids' widget="one2many" context="{'tree_view_ref': 'module.tree_view_ref'}" />
                </sheet>
            </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;
        serverData.views["product,module.tree_view_ref,list"] = /*xml */ `<tree><field name="display_name"/></tree>`;

        const mockRPC = (route, args) => {
            if (route === "/web_studio/create_inline_view") {
                assert.equal(args.context.tree_view_ref, 'module.tree_view_ref',
                    "context tree_view_ref should be propagated for inline view creation");

                const { model, field_name, subview_type, subview_xpath, view_id } = args;
                assert.strictEqual(model, "product");
                assert.strictEqual(field_name, "product_ids");
                assert.strictEqual(subview_type, "tree");
                assert.strictEqual(subview_xpath, "");
                assert.strictEqual(view_id, 1);

                // hardcode inheritance mechanisme
                serverData.views["coucou,1,form"] = /*xml */ `
                    <form>
                        <sheet>
                            <field name='display_name'/>
                            <field name='product_ids'>${serverData.views["product,module.tree_view_ref,list"]}</field>
                        </sheet>
                    </form>`;
                return serverData.views["product,module.tree_view_ref,list"];
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer .o_field_one2many'));
        await testUtils.dom.click($($(target).find('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many')[0]));
        await legacyExtraNextTick();
    });

    QUnit.test('edit one2many form view (2 level) and check chatter allowed', async function (assert) {
        assert.expect(6);

        patchWithCleanup(framework, {
            blockUI: () => Promise.resolve(),
            unblockUI: () => Promise.resolve()
        });

        const coucouId1 = pyEnv['coucou'].create({
            display_name: 'Coucou 11',
            product_ids: pyEnv['product'].search([['display_name', '=', 'xpad']]),
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = coucouId1;
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <form>
                            <sheet>
                                <group>
                                    <field name='partner_ids'>
                                        <form><sheet><group><field name='display_name'/></group></sheet></form>
                                    </field>
                                </group>
                            </sheet>
                        </form>
                    </field>
                </sheet>
            </form>`;

        Object.assign(serverData.views, {
            "product,2,list": "<tree><field name='display_name'/></tree>",
            "partner,3,list": "<tree><field name='display_name'/></tree>",
        });

    serverData.views["coucou,false,search"] = `<search></search>`;
    patchWithCleanup(MockServer.prototype, {
            mockEditView(args) {
                const result = this._super(...arguments);
                if (args.view_id !== 1) {
                    return result;
                }

                assert.ok(true, "should edit the view to add the one2many field");
                return result;
            }
        });

        const mockRPC = (route, args) => {
            if (route === "/web_studio/chatter_allowed") {
                return true;
            }
            if (args.method === 'name_search' && args.model === 'ir.model.fields') {
                assert.deepEqual(args.kwargs.args, [['relation', '=', 'partner'], ['ttype', 'in', ['many2one', 'many2many']], ['store', '=', true]],
                    "the domain should be correctly set when searching for a related field for new button");
                return Promise.resolve([]);
            }
        };

        const { webClient } = await start({
            serverData,
            mockRPC,
        });

        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);
        await testUtils.nextTick();

        assert.containsOnce(target, '.o_web_studio_add_chatter',
            "should be possible to add a chatter");

        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer .o_field_one2many'));
        await legacyExtraNextTick();
        await testUtils.dom.click(
            $(target).find('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'));
        await legacyExtraNextTick();
        assert.containsNone(target, '.o_web_studio_add_chatter',
            "should not be possible to add a chatter");

        await testUtils.dom.click($(target).find('.o_web_studio_view_renderer .o_field_one2many'));
        await testUtils.dom.click(
            $(target).find('.o_web_studio_view_renderer .o_field_one2many .o_web_studio_editX2Many[data-type="form"]')
        );
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.strictEqual($(target).find('.o_field_char').eq(0).text(), 'jean',
            "the partner view form should be displayed.");
        await testUtils.dom.dragAndDrop(
            $(target).find('.o_web_studio_new_fields .o_web_studio_field_char'),
            $(target).find('.o_inner_group .o_web_studio_hook:first')
        );

        // add a new button
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_web_studio_button_hook'));
        assert.strictEqual($('.modal .o_web_studio_new_button_dialog').length, 1,
            "there should be an opened modal to add a button");
        await testUtils.dom.click($('.modal .o_web_studio_new_button_dialog .js_many2one_field input'));
    });

    QUnit.test('edit one2many list view that uses parent key [REQUIRE FOCUS]', async function (assert) {
        // Skipped: need "parent." thing
        assert.expect(3);

        const coucouId1 = pyEnv['coucou'].create({
            display_name: 'Coucou 11',
            product_ids: pyEnv['product'].search([['display_name', '=', 'xpad']]),
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = coucouId1;
        serverData.views["coucou,1,form"] = /*xml */ `
           <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <form>
                            <sheet>
                                <field name="m2o"
                                       attrs="{'invisible': [('parent.display_name', '=', 'coucou')]}"
                                       domain="[('display_name', '=', parent.display_name)]" />
                            </sheet>
                        </form>
                    </field>
                </sheet>
            </form>`;

        Object.assign(serverData.views, {
            "product,2,list": "<tree><field name='display_name'/></tree>",
        });

        serverData.views["coucou,false,search"] = `<search></search>`;

        const webClient = await createEnterpriseWebClient({ serverData, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // edit the x2m form view
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_one2many'));
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'));
        await legacyExtraNextTick();
        assert.strictEqual($(target).find('.o_web_studio_form_view_editor .o_field_widget[name="m2o"]').text(), "jacques",
            "the x2m form view should be correctly rendered");
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_widget[name="m2o"]'));

        // open the domain editor
        assert.strictEqual($('.modal .o_domain_selector').length, 0,
            "the domain selector should not be opened");
        $(target).find('.o_web_studio_sidebar_content input[name="domain"]').trigger('focus');
        await testUtils.nextTick();
        assert.strictEqual($('.modal .o_domain_selector').length, 1,
            "the domain selector should be correctly opened");
    });

    QUnit.test('move a field in one2many list', async function (assert) {
        assert.expect(2);

        patchWithCleanup(framework, {
            blockUI: () => Promise.resolve(),
            unblockUI: () => Promise.resolve()
        });

        const coucouId1 = pyEnv['coucou'].create({
            display_name: 'Coucou 11',
            product_ids: pyEnv['product'].search([['display_name', '=', 'xpad']]),
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = coucouId1;
        serverData.views["coucou,1,form"] = /*xml */ `
            <form>
                <sheet>
                    <field name='display_name'/>
                    <field name='product_ids'>
                        <tree>
                            <field name='m2o'/>
                            <field name='coucou_id'/>
                        </tree>
                    </field>
                </sheet>
            </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;

        patchWithCleanup(MockServer.prototype, {
            mockEditView(args) {
                const result = this._super(...arguments);
                if (args.view_id !== 1) {
                    return result;
                }
                assert.deepEqual(args.operations[0], {
                    node: {
                        tag: 'field',
                        attrs: {name: 'coucou_id'},
                        subview_xpath: "//field[@name='product_ids']/tree",
                    },
                    position: 'before',
                    target: {
                        tag: 'field',
                        attrs: {name: 'm2o'},
                        subview_xpath: "//field[@name='product_ids']/tree",
                        xpath_info: [
                            {
                                indice: 1,
                                tag: 'tree',
                            },
                            {
                                indice: 1,
                                tag: 'field',
                            },
                        ],
                    },
                    type: 'move',
                }, "the move operation should be correct");
                return result;
            },
        });

        const webClient = await createEnterpriseWebClient({ serverData, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // edit the x2m form view
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_one2many'));
        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="list"]'));
        await legacyExtraNextTick();

        assert.strictEqual($(target).find('.o_web_studio_list_view_editor th').text(), "M2Ocoucou",
            "the columns should be in the correct order");

        // move coucou at index 0
        await testUtils.dom.dragAndDrop($(target).find('.o_web_studio_list_view_editor th:contains(coucou)'),
            $(target).find('th.o_web_studio_hook:first'));
    });

    QUnit.test('notebook and group drag and drop after a group', async function (assert) {
        assert.expect(2);
        var arch = "<form><sheet>" +
                "<group>" +
                    "<field name='display_name'/>" +
                "</group>" +
            "</sheet></form>";
        var vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
        });
        var $afterGroupHook = vem.$('.o_form_sheet > .o_web_studio_hook');
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_tabs'),
            $afterGroupHook, {disableDrop: true});
        assert.containsOnce(vem, '.o_web_studio_nearest_hook', "There should be 1 highlighted hook");
        await testUtils.dom.dragAndDrop(vem.$('.o_web_studio_field_type_container .o_web_studio_field_columns'),
            $afterGroupHook, {disableDrop: true});
        assert.containsOnce(vem, '.o_web_studio_nearest_hook', "There should be 1 highlighted hook");
    });

    QUnit.test('One2Many list editor column_invisible in attrs ', async function (assert) {
        // Skipped: need "parent." thing
        assert.expect(2);

        patchWithCleanup(framework, {
            blockUI: () => Promise.resolve(),
            unblockUI: () => Promise.resolve()
        });

        pyEnv['coucou'].create({
            display_name: 'Coucou 11',
            product_ids: pyEnv['product'].search([['display_name', '=', 'xpad']]),
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        serverData.views["coucou,1,form"] = /*xml */ `
        <form>
            <field name='product_ids'>
                <tree>
                    <field name="display_name" attrs="{\'column_invisible\': [(\'parent.id\', \'=\',False)]}" />
                </tree>
            </field>
        </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;

        patchWithCleanup(MockServer.prototype, {
            mockEditView(args) {
                const result = this._super(...arguments);
                if (args.view_id !== 1) {
                    return result;
                }
                assert.equal(args.operations[0].new_attrs.attrs, '{"column_invisible": [["parent.id","=",False]]}',
                    'we should send "column_invisible" in attrs.attrs');

                assert.equal(args.operations[0].new_attrs.readonly, '1',
                    'We should send "readonly" in the node attr');
                return result;
            }
        });

        const webClient = await createEnterpriseWebClient({ serverData, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        // Enter edit mode of the O2M
        await testUtils.dom.click($(target).find('.o_field_one2many[name=product_ids]'));
        await testUtils.dom.click($(target).find('.o_web_studio_editX2Many[data-type="list"]'));
        await legacyExtraNextTick();

        await testUtils.dom.click($(target).find('.o_web_studio_sidebar').find('.o_web_studio_view'));
        await testUtils.dom.click($(target).find('.o_web_studio_sidebar').find('input#show_invisible'));

        // select the first column
        await testUtils.dom.click($(target).find('thead th[data-node-id=1]'));
        // enable readonly
        await testUtils.dom.click($(target).find('.o_web_studio_sidebar').find('input#readonly'));
    });

    QUnit.test("One2Many form datapoint doesn't contain the parent datapoint", async function (assert) {
        /*
        * OPW-2125214
        * When editing a child o2m form with studio, the fields_get method tries to load
        * the parent fields too. This is not allowed anymore by the ORM.
        * It happened because, before, the child datapoint contained the parent datapoint's data
        */
        assert.expect(1);

        const coucouId1 = pyEnv['coucou'].create({
            display_name: 'Coucou 11',
            product_ids: [],
        });

        const action = serverData.actions["studio.coucou_action"];
        action.views = [[1, "form"]];
        action.res_model = "coucou";
        action.res_id = coucouId1;
        serverData.views["coucou,1,form"] = /*xml */ `
           <form>
               <field name='product_ids'>
                    <form>
                        <field name="display_name" />
                        <field name="toughness" />
                    </form>
               </field>
           </form>`;

        serverData.views["coucou,false,search"] = `<search></search>`;
        serverData.views["product,2,list"] = `<tree><field name="display_name" /></tree>`;

        const mockRPC = async (route, args) => {
            if (args.method === "onchange" && args.model === "product") {
                const fields = args.args[3];
                assert.deepEqual(Object.keys(fields), ["display_name", "toughness"]);
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true}});
        await doAction(webClient, "studio.coucou_action");
        await openStudio(target);

        await testUtils.dom.click($(target).find('.o_web_studio_form_view_editor .o_field_one2many'));
        await testUtils.dom.click(
            $(target).find('.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]')
        );
        await legacyExtraNextTick();
    });

    QUnit.test('folds/unfolds the existing fields into sidebar', async function (assert) {
        assert.expect(10);

        const arch = `<form>
            <group>
                <field name="display_name"/>
            </group>
        </form>`;

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC: function (route) {
                if (route === '/web_studio/edit_view') {
                    const newArch = `<form>
                        <group>
                            <field name="char_field"/>
                            <field name="display_name"/>
                        </group>
                    </form>`;
                    return getCurrentMockServer()._mockReturnView(newArch, "coucou");
                }
            },
        });


        assert.containsN(vem, '.o_web_studio_field_type_container', 3,
            "there should be three sections in Add (new & existing fields & Components");
        assert.hasClass(vem.el.querySelector('.o_web_studio_existing_fields_icon'), 'fa-caret-right',
            "should have a existing fields folded");
        assert.isNotVisible(vem.el.querySelector('.o_web_studio_existing_fields_section'),
            "the existing fields section should not be visible");

        // Unfold the existing fields section
        await testUtils.dom.click(vem.el.querySelector('.o_web_studio_existing_fields_icon'));

        assert.containsN(vem, '.o_web_studio_field_type_container', 3,
            "there should be three sections in Add (new & existing fields & Components");
        assert.hasClass(vem.el.querySelector('.o_web_studio_existing_fields_icon'), 'fa-caret-down',
            "should have a existing fields unfolded");
        assert.isVisible(vem.el.querySelector('.o_web_studio_existing_fields_section'),
            "the existing fields section should be visible");

        // drag and drop the new char field
        await testUtils.dom.dragAndDrop(vem.el.querySelector('.o_web_studio_existing_fields .o_web_studio_field_char'),
            vem.el.querySelector('.o_inner_group .o_web_studio_hook'));
        assert.isVisible(vem.el.querySelector('.o_web_studio_existing_fields_section'),
            "keep the existing fields section visible when adding the new field");

        // fold the existing fields section
        await testUtils.dom.click(vem.el.querySelector('.o_web_studio_existing_fields_icon'));

        assert.containsN(vem, '.o_web_studio_field_type_container', 3,
            "there should be three sections in Add (new & existing fields & Components");
        assert.hasClass(vem.el.querySelector('.o_web_studio_existing_fields_icon'), 'fa-caret-right',
            "should have a existing fields folded");
        assert.isNotVisible(vem.el.querySelector('.o_web_studio_existing_fields_section'),
            "the existing fields section should not be visible");

    });

    QUnit.test('open xml editor of component view', async function (assert) {
        assert.expect(1);

        // the XML editor button is only available in debug mode
        const initialDebugMode = odoo.debug;
        odoo.debug = true;

        // the XML editor lazy loads its libs and its templates so its start
        // method is monkey-patched to know when the widget has started
        const xmlEditorDef = testUtils.makeTestPromise();
        testUtils.mock.patch(ace, {
            start: function () {
                return this._super(...arguments).then(function () {
                    xmlEditorDef.resolve();
                });
            },
        });

        const arch = '<pivot />';
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC(route) {
                if (route === '/web_editor/get_assets_editor_resources') {
                    return Promise.resolve({
                        views: [{
                            active: true,
                            arch: arch,
                            id: 1,
                            inherit_id: false,
                            name: "base view",
                        }, {
                            active: true,
                            arch: "<data/>",
                            id: 42,
                            inherit_id: 1,
                            name: "studio view",
                        }],
                        scss: [],
                        js: [],
                    });
                }
            },
            viewID: 1,
            studioViewID: 42,
        });

        await testUtils.dom.click(vem.$('.o_web_studio_xml_editor'));
        await xmlEditorDef;

        assert.containsOnce(vem, '.o_ace_view_editor', "the XML editor should be opened");

        odoo.debug = initialDebugMode;
        testUtils.mock.unpatch(ace);

    });

    QUnit.test('existing field section should be unfolded by default in kanban', async function (assert) {
        assert.expect(2);

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="o_kanban_record">
                                <field name="display_name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        await testUtils.dom.click(vem.el.querySelector('.o_web_studio_new'));
        assert.hasClass(vem.el.querySelector('.o_web_studio_existing_fields_icon'), 'fa-caret-down',
            "should have a existing fields unfolded");
        assert.isVisible(vem.el.querySelector('.o_web_studio_existing_fields_section'),
            "the existing fields section should be visible");

    });

    QUnit.test('existing field section should be unfolded by default in search', async function (assert) {
        assert.expect(2);

        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: `<search>
                    <field name='display_name'/>
                </search>`,
        });

        assert.hasClass(vem.el.querySelector('.o_web_studio_existing_fields_icon'), 'fa-caret-down',
            "should have a existing fields unfolded");
        assert.isVisible(vem.el.querySelector('.o_web_studio_existing_fields_section'),
            "the existing fields section should be visible");

    });

    QUnit.test('open xml editor of graph component view and close it', async function (assert) {
        assert.expect(5);

        // the XML editor button is only available in debug mode
        const initialDebugMode = odoo.debug;
        odoo.debug = true;

        // the XML editor lazy loads its libs and its templates so its start
        // method is monkey-patched to know when the widget has started
        const xmlEditorDef = testUtils.makeTestPromise();
        testUtils.mock.patch(ace, {
            start: function () {
                return this._super(...arguments).then(function () {
                    xmlEditorDef.resolve();
                });
            },
        });

        const arch = '<graph />';
        const vem = await studioTestUtils.createViewEditorManager({
            model: 'coucou',
            arch: arch,
            mockRPC(route) {
                if (route === '/web_editor/get_assets_editor_resources') {
                    return Promise.resolve({
                        views: [{
                            active: true,
                            arch: arch,
                            id: 1,
                            inherit_id: false,
                            name: "base view",
                        }, {
                            active: true,
                            arch: "<data/>",
                            id: 42,
                            inherit_id: 1,
                            name: "studio view",
                        }],
                        scss: [],
                        js: [],
                    });
                }
            },
            viewID: 1,
            studioViewID: 42,
        });

        await testUtils.dom.click(vem.$('.o_web_studio_xml_editor'));
        await xmlEditorDef;
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(vem, '.o_ace_view_editor', "the XML editor should be opened");
        assert.containsNone(vem, '.o_web_studio_sidebar');

        await testUtils.dom.click(".o_ace_view_editor .o_button_section button[data-action='close']");
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(vem, '.o_ace_view_editor');
        assert.containsOnce(vem, '.o_web_studio_sidebar');
        assert.containsOnce(vem, '.o_graph_renderer');

        odoo.debug = initialDebugMode;
        testUtils.mock.unpatch(ace);

    });
});
});

});
