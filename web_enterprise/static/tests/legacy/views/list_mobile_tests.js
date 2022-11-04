odoo.define('web_enterprise.list_mobile_tests', function (require) {
    "use strict";

    const ListRenderer = require('web.ListRenderer');
    const ListView = require('web.ListView');
    const testUtils = require('web.test_utils');

    const { createView, dom, mock } = testUtils;

    QUnit.module("LegacyViews", {
        beforeEach() {
            this.data = {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                    },
                    records: [
                        { id: 1, bar: true, foo: "yop" },
                        { id: 2, bar: true, foo: "blip" },
                        { id: 3, bar: true, foo: "gnap" },
                        { id: 4, bar: false, foo: "blip" },
                    ],
                },
            };
            mock.patch(ListRenderer, {
                init() {
                    this._super(...arguments);
                    this.LONG_TOUCH_THRESHOLD = 0;
                }
            });
        },
        afterEach() {
            mock.unpatch(ListRenderer);
        },
    }, function () {

        QUnit.module("ListView (legacy) - Mobile");

        QUnit.test("selection is properly displayed (single page)", async function (assert) {
            assert.expect(10);

            const list = await createView({
                touchScreen: true,
                arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="bar"/>
                    </tree>`,
                data: this.data,
                model: 'foo',
                viewOptions: { hasActionMenus: true },
                View: ListView,
            });

            assert.containsN(list, '.o_data_row', 4);
            assert.containsNone(list, '.o_list_selection_box');

            // select a record
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchend');
            assert.containsOnce(list, '.o_list_selection_box');
            assert.containsNone(list.$('.o_list_selection_box'), '.o_list_select_domain');
            assert.ok(list.$('.o_list_selection_box').text().includes("1 selected"))
            // unselect a record
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchend');
            assert.containsNone(list.$('.o_list_selection_box'), '.o_list_select_domain');

            // select 2 records
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchend');
            await dom.triggerEvent(list.$('.o_data_row:eq(1)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(1)'), 'touchend');
            assert.ok(list.$('.o_list_selection_box').text().includes("2 selected"))
            assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');
            await testUtils.controlPanel.toggleActionMenu(list);
            assert.deepEqual(testUtils.controlPanel.getMenuItemTexts(list), ['Delete'],
                'action menu should contain the Delete action');
            // unselect all
            await dom.click(list.$('.o_discard_selection'));
            await testUtils.nextTick();
            assert.containsNone(list, '.o_list_selection_box');

            list.destroy();
        });

        QUnit.test("selection box is properly displayed (multi pages)", async function (assert) {
            assert.expect(13);
            const list = await createView({
                touchScreen: true,
                arch: `
                    <tree limit="3">
                        <field name="foo"/>
                        <field name="bar"/>
                    </tree>`,
                data: this.data,
                model: 'foo',
                View: ListView,
                viewOptions: { hasActionMenus: true },
            });

            assert.containsN(list, '.o_data_row', 3);
            assert.containsNone(list, '.o_list_selection_box');

            // select a record
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchend');

            assert.containsOnce(list, '.o_list_selection_box');
            assert.containsNone(list.$('.o_list_selection_box'), '.o_list_select_domain');
            assert.strictEqual(list.$('.o_list_selection_box').text().replace(/\s+/g, ' '),
                " × 1 selected ");
            assert.containsOnce(list, '.o_list_selection_box');
            assert.containsOnce(list.el, 'div.o_control_panel .o_cp_action_menus');
            await testUtils.controlPanel.toggleActionMenu(list);
            assert.deepEqual(testUtils.controlPanel.getMenuItemTexts(list), ['Delete'],
                'action menu should contain the Delete action');
            // select all records of first page
            await dom.triggerEvent(list.$('.o_data_row:eq(1)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(1)'), 'touchend');
            await dom.triggerEvent(list.$('.o_data_row:eq(2)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(2)'), 'touchend');
            assert.containsOnce(list, '.o_list_selection_box');
            assert.containsOnce(list.$('.o_list_selection_box'), '.o_list_select_domain');
            assert.strictEqual(list.$('.o_list_selection_box').text().replace(/\s+/g, ' ').trim(),
                "× 3 selected Select all 4");

            // select all domain
            await dom.click(list.$('.o_list_selection_box .o_list_select_domain'));

            assert.containsOnce(list, '.o_list_selection_box');
            assert.strictEqual(list.$('.o_list_selection_box').text().replace(/\s+/g, ' ').trim(),
                "× All 4 selected");

            list.destroy();
        });

        QUnit.test("export button is properly hidden", async function (assert) {
            assert.expect(2);

            const list = await createView({
                touchScreen: true,
                arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="bar"/>
                    </tree>`,
                data: this.data,
                model: 'foo',
                View: ListView,
                session: {
                    async user_has_group(group) {
                        if (group === 'base.group_allow_export') {
                            return true;
                        }
                        return this._super(...arguments);
                    },
                },
            });

            assert.containsN(list, '.o_data_row', 4);
            assert.isNotVisible(list.$buttons.find('.o_list_export_xlsx'));

            list.destroy();
        });

        QUnit.test('editable readonly list view is disabled', async function (assert) {
            assert.expect(1);

            const list = await createView({
                touchScreen: true,
                arch: `
                    <tree>
                        <field name="foo"/>
                    </tree>`,
                data: this.data,
                model: 'foo',
                View: ListView,
            });
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchstart');
            await dom.triggerEvent(list.$('.o_data_row:eq(0)'), 'touchend');
            await testUtils.dom.click(list.$('.o_data_row:eq(0) .o_data_cell:eq(0)'));
            assert.containsNone(list, '.o_selected_row .o_field_widget[name=foo]',
                "The listview should not contains an edit field");
            list.destroy();
        });

        QUnit.test("add custom field button not shown in mobile (with opt. col.)", async function (assert) {
            assert.expect(3);

            const list = await testUtils.createView({
                arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="bar" optional="hide"/>
                    </tree>`,
                data: this.data,
                model: 'foo',
                touchScreen: true,
                View: ListView,
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
                arch: `
                    <tree>
                        <field name="foo"/>
                        <field name="bar"/>
                    </tree>`,
                data: this.data,
                model: 'foo',
                touchScreen: true,
                View: ListView,
            });
            assert.containsNone(list.$('table'), '.o_optional_columns_dropdown_toggle');
            list.destroy();
        });
    });
});
