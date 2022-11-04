odoo.define('web_enterprise.kanban_mobile_tests', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const { createView, dom} = require('web.test_utils');

QUnit.module('LegacyViews', {
    beforeEach() {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "my float", type: "float"},
                    product_id: {string: "something_id", type: "many2one", relation: "product"},
                    category_ids: { string: "categories", type: "many2many", relation: 'category'},
                    state: { string: "State", type: "selection", selection: [["abc", "ABC"], ["def", "DEF"], ["ghi", "GHI"]]},
                    date: {string: "Date Field", type: 'date'},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                },
                records: [
                    {id: 1, bar: true, foo: "yop", int_field: 10, qux: 0.4, product_id: 3, state: "abc", category_ids: []},
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13, product_id: 5, state: "def", category_ids: [6]},
                    {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3, product_id: 3, state: "ghi", category_ids: [7]},
                    {id: 4, bar: false, foo: "blip", int_field: -4, qux: 9, product_id: 5, state: "ghi", category_ids: []},
                    {id: 5, bar: false, foo: "Hello \"World\"! #peace_n'_love", int_field: -9, qux: 10, state: "jkl", category_ids: []},
                ]
            },
            product: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    name: {string: "Display Name", type: "char"},
                },
                records: [
                    {id: 3, name: "hello"},
                    {id: 5, name: "xmo"},
                ]
            },
            category: {
                fields: {
                    name: {string: "Category Name", type: "char"},
                    color: {string: "Color index", type: "integer"},
                },
                records: [
                    {id: 6, name: "gold", color: 2},
                    {id: 7, name: "silver", color: 5},
                ]
            },
        };
    },
}, function () {
    QUnit.module("KanbanView (legacy) - Mobile")
    QUnit.test('kanban with searchpanel: rendering in mobile', async function (assert) {
        assert.expect(34);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: `
                <kanban>
                    <templates><t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>
            `,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="product_id" expand="1" enable_counters="1"/>
                            <field name="state" expand="1" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>
                `,
            },
            mockRPC(route, {method}) {
                if (method && method.includes('search_panel_')) {
                    assert.step(method);
                }
                return this._super.apply(this, arguments);
            },
        });

        let $sp = kanban.$(".o_search_panel");

        assert.containsOnce(kanban, ".o_search_panel.o_search_panel_summary");
        assert.containsNone(document.body, "div.o_search_panel.o_searchview.o_mobile_search");
        assert.verifySteps([
            "search_panel_select_range",
            "search_panel_select_multi_range",
        ]);

        assert.containsOnce($sp, ".fa.fa-filter");
        assert.containsOnce($sp, ".o_search_panel_current_selection:contains(All)");

        // open the search panel
        await dom.click($sp);
        $sp = $(".o_search_panel");

        assert.containsNone(kanban, ".o_search_panel.o_search_panel_summary");
        assert.containsOnce(document.body, "div.o_search_panel.o_searchview.o_mobile_search");

        assert.containsOnce($sp, ".o_mobile_search_header > button:contains(FILTER)");
        assert.containsOnce($sp, "button.o_mobile_search_footer:contains(SEE RESULT)");
        assert.containsN($sp, ".o_search_panel_section", 2);
        assert.containsOnce($sp, ".o_search_panel_section.o_search_panel_category");
        assert.containsOnce($sp, ".o_search_panel_section.o_search_panel_filter");
        assert.containsN($sp, ".o_search_panel_category_value", 3);
        assert.containsOnce($sp, ".o_search_panel_category_value > header.active", 3);
        assert.containsN($sp, ".o_search_panel_filter_value", 3);

        // select category
        await dom.click($sp.find(".o_search_panel_category_value:contains(hello) header"));

        assert.verifySteps([
            "search_panel_select_range",
            "search_panel_select_multi_range",
        ]);

        // select filter
        await dom.click($sp.find(".o_search_panel_filter_value:contains(DEF) input"));

        assert.verifySteps([
            "search_panel_select_range",
            "search_panel_select_multi_range",
        ]);

        // close with back button
        await dom.click($sp.find(".o_mobile_search_header button"));
        $sp = $(".o_search_panel");

        assert.containsOnce(kanban, ".o_search_panel.o_search_panel_summary");
        assert.containsNone(document.body, "div.o_search_panel.o_searchview.o_mobile_search");

        // selection is kept when closed

        assert.containsOnce($sp, ".o_search_panel_current_selection");
        assert.containsOnce($sp, ".o_search_panel_category:contains(hello)");
        assert.containsOnce($sp, ".o_search_panel_filter:contains(DEF)");

        // open the search panel
        await dom.click($sp);
        $sp = $(".o_search_panel");

        assert.containsOnce($sp, ".o_search_panel_category_value > header.active:contains(hello)");
        assert.containsOnce($sp, ".o_search_panel_filter_value:contains(DEF) input:checked");

        assert.containsNone(kanban, ".o_search_panel.o_search_panel_summary");
        assert.containsOnce(document.body, "div.o_search_panel.o_searchview.o_mobile_search");

        // close with bottom button
        await dom.click($sp.find("button.o_mobile_search_footer"));

        assert.containsOnce(kanban, ".o_search_panel.o_search_panel_summary");
        assert.containsNone(document.body, "div.o_search_panel.o_searchview.o_mobile_search");

        kanban.destroy();
    });


    QUnit.module('KanbanView Mobile');

    QUnit.test('mobile no quick create column when grouping on non m2o field', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test o_kanban_small_column" on_create="quick_create">' +
                '<templates><t t-name="kanban-box">' +
                '<div><field name="foo"/></div>' +
                '<div><field name="int_field"/></div>' +
                '</t></templates>' +
                '</kanban>',
            groupBy: ['int_field'],
        });

        assert.containsNone(kanban, '.o_kanban_mobile_add_column', "should not have the add column button");
        assert.containsNone(kanban.$('.o_column_quick_create'),
            "should not have column quick create tab as we grouped records on integer field");
        kanban.destroy();
    });

    QUnit.test("autofocus quick create form", async function (assert) {
        assert.expect(2);

        const kanban = await createView({
            View: KanbanView,
            model: "partner",
            data: this.data,
            arch: `<kanban on_create="quick_create">
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            groupBy: ["product_id"],
        });

        // quick create in first column
        await dom.click(kanban.$buttons.find(".o-kanban-button-new"));
        assert.ok(kanban.$(".o_kanban_group:nth(0) > div:nth(1)").hasClass("o_kanban_quick_create"),
            "clicking on create should open the quick_create in the first column");
        assert.strictEqual(document.activeElement, kanban.$(".o_kanban_quick_create .o_input:first")[0],
            "the first input field should get the focus when the quick_create is opened");

        kanban.destroy();
    });
});
});
