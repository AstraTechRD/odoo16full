odoo.define('web_enterprise.list_tests', function (require) {
"use strict";

const AbstractStorageService = require('web.AbstractStorageService');
const ListRenderer = require('web.ListRenderer');
const ListView = require('web.ListView');
const RamStorage = require('web.RamStorage');
const testUtils = require('web.test_utils');
const { unblockUI } = require('web.framework');
const { patch, unpatch, UnknownPatchError } = require('web.utils');
const PromoteStudioDialog = require('web_enterprise.PromoteStudioDialog');

QUnit.module('web_enterprise', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                },
                records: [
                    {id: 1, bar: true, foo: "yop"},
                    {id: 2, bar: true, foo: "blip"},
                    {id: 3, bar: true, foo: "gnap"},
                    {id: 4, bar: false, foo: "blip"},
                ]
            }
        };

        this.RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });
    }
}, function () {

    QUnit.module('ListView (Legacy)');

    QUnit.test("add custom field button with other optional columns - studio not installed", async function (assert) {
        assert.expect(11);

        let listPatch;
        try {
            listPatch = unpatch(ListRenderer.prototype, 'web_studio.ListRenderer');
        } catch (e) {
            if (!(e instanceof UnknownPatchError)) {
                throw e;
            }
        }

        testUtils.mock.patch(PromoteStudioDialog, {
            _reloadPage: function () {
                assert.step('window_reload');
                unblockUI(); // the UI is normally unblocked by the reload
            }
        });

        const list = await testUtils.createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar" optional="hide"/>
                </tree>`,
            session: {
                is_system: true
            },
            action: {
                xml_id: "action_43",
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'ir.module.module') {
                    assert.step('studio_module_id');
                    return Promise.resolve([{id: 42}]);
                }
                if (args.method === 'button_immediate_install' && args.model === 'ir.module.module') {
                    assert.deepEqual(args.args[0], [42], "Should be the id of studio module returned by the search read");
                    assert.step('studio_module_install');
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
            services: {
                local_storage: this.RamStorageService,
            },
        });

        assert.ok(list.$('.o_data_row').length > 0);
        assert.containsOnce(list.$('table'), '.o_optional_columns_dropdown_toggle');
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        const $dropdown = list.$('div.o_optional_columns');
        assert.containsOnce($dropdown, 'div.dropdown-item');
        assert.containsOnce($dropdown, 'button.dropdown-item-studio');

        await testUtils.dom.click(list.$('div.o_optional_columns button.dropdown-item-studio'));
        await testUtils.nextTick();
        assert.containsOnce(document.body, '.modal-studio');
        await testUtils.dom.click($('.modal-studio .o_install_studio'));
        assert.equal(window.localStorage.openStudioOnReload, 'main');
        assert.verifySteps(['studio_module_id', 'studio_module_install', 'window_reload']);
        // wash localStorage
        window.localStorage.openStudioOnReload = false;

        testUtils.mock.unpatch(PromoteStudioDialog);
        if (listPatch) {
            patch(ListRenderer.prototype, 'web_studio.ListRenderer', listPatch);
        }
        list.destroy();
    });

    QUnit.test("add custom field button without other optional columns - studio not installed", async function (assert) {
        assert.expect(11);

        let listPatch;
        try {
            listPatch = unpatch(ListRenderer.prototype, 'web_studio.ListRenderer');
        } catch (e) {
            if (!(e instanceof UnknownPatchError)) {
                throw e;
            }
        }

        testUtils.mock.patch(PromoteStudioDialog, {
            _reloadPage: function () {
                assert.step('window_reload');
                unblockUI(); // the UI is normally unblocked by the reload
            }
        });

        const list = await testUtils.createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            session: {
                is_system: true
            },
            action: {
                xml_id: "action_43",
            },
            mockRPC: function (route, args) {
                if (args.method === 'search_read' && args.model === 'ir.module.module') {
                    assert.step('studio_module_id');
                    return Promise.resolve([{id: 42}]);
                }
                if (args.method === 'button_immediate_install' && args.model === 'ir.module.module') {
                    assert.deepEqual(args.args[0], [42], "Should be the id of studio module returned by the search read");
                    assert.step('studio_module_install');
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
            services: {
                local_storage: this.RamStorageService,
            },
        });

        assert.ok(list.$('.o_data_row').length > 0);
        assert.containsOnce(list.$('table'), '.o_optional_columns_dropdown_toggle');
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        const $dropdown = list.$('div.o_optional_columns');
        assert.containsNone($dropdown, 'div.dropdown-item');
        assert.containsOnce($dropdown, 'button.dropdown-item-studio');

        await testUtils.dom.click(list.$('div.o_optional_columns button.dropdown-item-studio'));
        await testUtils.nextTick();
        assert.containsOnce(document.body, '.modal-studio');
        await testUtils.dom.click($('.modal-studio .o_install_studio'));
        assert.equal(window.localStorage.openStudioOnReload, 'main');
        assert.verifySteps(['studio_module_id', 'studio_module_install', 'window_reload']);
        // wash localStorage
        window.localStorage.openStudioOnReload = false;

        if (listPatch) {
            patch(ListRenderer.prototype, 'web_studio.ListRenderer', listPatch);
        }
        testUtils.mock.unpatch(PromoteStudioDialog);
        list.destroy();
    });

    QUnit.test("add custom field button not shown to non-system users (with opt. col.)", async function (assert) {
        assert.expect(3);

        const list = await testUtils.createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar" optional="hide"/>
                </tree>`,
            session: {
                is_system: false
            },
            action: {
                xml_id: "action_43",
            },
        });
        assert.containsOnce(list.$('table'), '.o_optional_columns_dropdown_toggle');
        await testUtils.dom.click(list.$('table .o_optional_columns_dropdown_toggle'));
        const $dropdown = list.$('div.o_optional_columns');
        assert.containsOnce($dropdown, 'div.dropdown-item');
        assert.containsNone($dropdown, 'button.dropdown-item-studio');

        list.destroy();
    });

    QUnit.test("add custom field button not shown to non-system users (wo opt. col.)", async function (assert) {
        assert.expect(1);
        const list = await testUtils.createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            session: {
                is_system: false
            },
            action: {
                xml_id: "action_43",
            },
        });
        assert.containsNone(list.$('table'), '.o_optional_columns_dropdown_toggle');
        list.destroy();
    });

    QUnit.test("add custom field button not shown with invalid action", async function (assert) {
        assert.expect(1);
        const list = await testUtils.createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `
                <tree>
                    <field name="foo"/>
                    <field name="bar"/>
                </tree>`,
            session: {
                is_system: true
            },
            action: {
                xml_id: null,
            },
        });
        assert.containsNone(list.$('div.o_optional_columns'), 'button.dropdown-item-studio');
        list.destroy();
    });

});
});
