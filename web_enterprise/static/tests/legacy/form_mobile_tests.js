odoo.define('web_enterprise.form_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('web_enterprise', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    trululu: 4,
                }, {
                    id: 2,
                    display_name: "second record",
                    trululu: 1,
                }, {
                    id: 4,
                    display_name: "aaa",
                }],
            },
        };
    },
}, function () {

    QUnit.module('Mobile FormView');

    QUnit.test('statusbar buttons are correctly rendered in mobile', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header>' +
                        '<button string="Confirm"/>' +
                        '<button string="Do it"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<button name="display_name"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_statusbar_buttons a:contains(Action)').length, 1,
            "statusbar should contain a button 'Action'");
        assert.containsOnce(form, '.o_statusbar_buttons .dropdown-menu',
            "statusbar should contain a dropdown");
        assert.containsNone(form, '.o_statusbar_buttons .dropdown-menu:visible',
            "dropdown should be hidden");

        // open the dropdown
        await testUtils.dom.click(form.$('.o_statusbar_buttons a'));
        assert.containsOnce(form, '.o_statusbar_buttons .dropdown-menu:visible',
            "dropdown should be visible");
        assert.containsN(form, '.o_statusbar_buttons .dropdown-menu > button', 2,
            "dropdown should contain 2 buttons");

        form.destroy();
    });

    QUnit.test('statusbar "Action" button should be displayed only if there are multiple visible buttons', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<header>' +
                        '<button string="Confirm" attrs=\'{"invisible": [["display_name", "=", "first record"]]}\'/>' +
                        '<button string="Do it" attrs=\'{"invisible": [["display_name", "=", "first record"]]}\'/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // if all buttons are invisible then there should be no action button
        assert.containsNone(form, '.o_statusbar_buttons > btn-group > .dropdown-toggle',
            "'Action' dropdown is not displayed as there are no visible buttons");
        // there should be two invisible buttons
        assert.containsN(form, '.o_statusbar_buttons > button.o_invisible_modifier', 2,
            "Status bar should have two buttons with 'o_invisible_modifier' class");

        // change display_name to update buttons modifiers and make it visible
        await testUtils.form.clickEdit(form);
        await testUtils.fields.editInput(form.$('input[name=display_name]'), 'test');
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.o_statusbar_buttons a:contains(Action)',
            "statusbar should contain a button 'Action'");
        assert.containsOnce(form, '.o_statusbar_buttons .dropdown-menu',
            "statusbar should contain a dropdown");

        form.destroy();
    });

    QUnit.test('statusbar "Action" button not displayed in edit mode with .oe_read_only button', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `
                <form>
                    <header>
                        <button string="Share" type="action" class="oe_highlight oe_read_only"/>
                        <button string="Email" type="action" class="oe_highlight oe_read_only"/>
                    </header>
                    <sheet>
                        <group>
                            <field name="display_name"/>
                        </group>
                    </sheet>
                </form>
            `,
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsNone(form, '.o_statusbar_buttons a:contains(Action)',
            "'Action' button should not be there");
        await testUtils.form.clickSave(form);
        assert.containsOnce(form, '.o_statusbar_buttons a:contains(Action)',
            "'Action' button should be there");
        form.destroy();
    });

    QUnit.test(`statusbar "Action" button shouldn't be displayed for only one visible button`, async function (assert) {
        assert.expect(3);

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form>
                    <header>
                        <button string="Hola" attrs='{"invisible": [["display_name", "=", "first record"]]}'/>
                        <button string="Ciao"/>
                    </header>
                    <sheet>
                        <group>
                            <field name="display_name"/>
                        </group>
                    </sheet>
                </form>`,
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        // There should be a simple statusbar button and no action dropdown
        assert.containsNone(form, '.o_statusbar_buttons a:contains(Action)', "should have no 'Action' dropdown");
        assert.containsOnce(form, '.o_statusbar_buttons > button > span:contains(Ciao)', "should have a simple statusbar button 'Ciao'");

        // change display_name to update buttons modifiers and make both buttons visible
        await testUtils.fields.editInput(form.$('input[name=display_name]'), 'test');

        // Now there should an action dropdown, because there are two visible buttons
        assert.containsOnce(form, '.o_statusbar_buttons a:contains(Action)', "should have no 'Action' dropdown");

        form.destroy();
    });

    QUnit.test(`statusbar widgets should appear in the statusbar dropdown only if there are multiple items`, async function (assert) {
        assert.expect(4);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `
                <form string="Partners">
                    <header>
                        <widget name="attach_document" string="Attach document"/>
                        <button string="Ciao" attrs='{"invisible": [["display_name", "=", "first record"]]}'/>
                    </header>
                    <sheet>
                        <group>
                            <field name="display_name"/>
                        </group>
                    </sheet>
                </form>
            `,
            res_id: 2,
            viewOptions: {
                mode: 'edit',
            },
        });

        const dropdownActionButton = '.o_statusbar_buttons a:contains(Action)';

        // Now there should an action dropdown, because there are two visible buttons
        assert.containsOnce(form, dropdownActionButton, "should have 'Action' dropdown");

        assert.containsN(form, `.o_statusbar_buttons .dropdown-menu > button`,
            2, "should have 2 buttons in the dropdown");

        // change display_name to update buttons modifiers and make one button visible
        await testUtils.fields.editInput(form.$('input[name=display_name]'), 'first record');

        // There should be a simple statusbar button and no action dropdown
        assert.containsNone(form, dropdownActionButton, "shouldn't have 'Action' dropdown");
        assert.containsOnce(form, `.o_statusbar_buttons > button:visible`,
            "should have 1 button visible in the statusbar");

        form.destroy();
    });

    QUnit.test(`Quick Edition: quick edit many2one`, async function (assert) {
        assert.expect(1);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="trululu" />
                        </group>
                    </sheet>
                </form>
            `,
            archs: {
                'partner,false,kanban': `
                    <kanban>
                        <templates><t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="display_name"/>
                            </div>
                        </t></templates>
                    </kanban>
                `,
                'partner,false,search': '<search></search>',
            },
            res_id: 2,
        });

        await testUtils.dom.click(form.$('.o_form_label'));
        await testUtils.nextTick(); // wait for quick edit

        const $modal = $('.o_modal_full .modal-lg');
        assert.equal($modal.length, 1, 'there should be one modal opened in full screen');

        form.destroy();
    });

    QUnit.test('statusbar "Action" dropdown should keep its open/close state', async function (assert) {
        assert.expect(5);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `
                <form>
                    <header>
                        <button string="Just more than one"/>
                        <button string="Confirm" attrs='{"invisible": [["display_name", "=", ""]]}'/>
                        <button string="Do it" attrs='{"invisible": [["display_name", "!=", ""]]}'/>
                    </header>
                    <sheet>
                        <field name="display_name"/>
                    </sheet>
                </form>
            `,
        });

        const dropdownMenuSelector = '.o_statusbar_buttons .dropdown-menu';
        assert.containsOnce(form, dropdownMenuSelector,
            "statusbar should contain a dropdown");
        assert.doesNotHaveClass(form.el.querySelector(dropdownMenuSelector), 'show',
            "dropdown should be closed");

        // open the dropdown
        await testUtils.dom.click(form.el.querySelector('.o_statusbar_buttons .dropdown-toggle'));
        assert.hasClass(form.el.querySelector(dropdownMenuSelector), 'show',
            "dropdown should be opened");

        // change display_name to update buttons' modifiers
        await testUtils.fields.editInput(form.el.querySelector('input[name="display_name"]'), 'test');
        assert.containsOnce(form, dropdownMenuSelector,
            "statusbar should contain a dropdown");
        assert.hasClass(form.el.querySelector(dropdownMenuSelector), 'show',
            "dropdown should still be opened");

        form.destroy();
    });

    QUnit.test(`statusbar "Action" dropdown's open/close state shouldn't be modified after 'onchange'`, async function (assert) {
        assert.expect(5);

        let resolveOnchange;
        const onchangePromise = new Promise(resolve => {
            resolveOnchange = resolve;
        });

        this.data.partner.onchanges = {
            display_name: async () => {},
        };

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `
                <form>
                    <header>
                        <button name="create" string="Create Invoice" type="action"/>
                        <button name="send" string="Send by Email" type="action"/>
                    </header>
                    <sheet>
                        <field name="display_name" />
                    </sheet>
                </form>
            `,
            async mockRPC(route, { method, args: [, , changedField] }) {
                return method === 'onchange' && changedField === 'display_name' ? onchangePromise : this._super(...arguments);
            },
        });

        const dropdownMenuSelector = '.o_statusbar_buttons .dropdown-menu';
        assert.containsOnce(form, dropdownMenuSelector,
            "statusbar should contain a dropdown");
        assert.doesNotHaveClass(form.el.querySelector(dropdownMenuSelector), 'show',
            "dropdown should be closed");

        await testUtils.fields.editInput(form.el.querySelector('input[name="display_name"]'), 'before onchange');
        await testUtils.dom.click(form.el.querySelector('.o_statusbar_buttons .dropdown-toggle'));
        assert.hasClass(form.el.querySelector(dropdownMenuSelector), 'show',
            "dropdown should be opened");
        resolveOnchange({ value: { display_name: 'after onchange' } });
        await testUtils.nextTick();
        assert.strictEqual(form.el.querySelector('input[name="display_name"]').value, 'after onchange');
        assert.hasClass(form.el.querySelector(dropdownMenuSelector), 'show',
            "dropdown should still be opened");

        form.destroy();
    });

    QUnit.test("preserve current scroll position on form view while closing dialog", async function (assert) {
        assert.expect(6);

        const form = await createView({
            View: FormView,
            arch: `<form>
                    <sheet>
                        <p style='height:500px'></p>
                        <field name="trululu"/>
                        <p style='height:500px'></p>
                    </sheet>
                </form>`,
            archs: {
                "partner,false,kanban": `<kanban>
                    <templates><t t-name="kanban-box">
                        <div class="oe_kanban_global_click"><field name="display_name"/></div>
                    </t></templates>
                </kanban>`,
                "partner,false,search": "<search></search>",
            },
            data: this.data,
            model: "partner",
            res_id: 2,
            debug: true, // need to be in the viewport to check scrollPosition
            viewOptions: { mode: "edit" },
        });

        const scrollPosition = { top: 265, left: 0 };
        window.scrollTo(scrollPosition);

        assert.strictEqual(window.scrollY, scrollPosition.top, "Should have scrolled 265 px vertically");
        assert.strictEqual(window.scrollX, scrollPosition.left, "Should be 0 px from left as it is");
        // click on m2o field
        await testUtils.dom.click(form.$(".o_field_many2one input"));
        assert.strictEqual(window.scrollY, 0, "Should have scrolled to top (0) px");
        assert.containsOnce($("body"), ".modal.o_modal_full", "there should be a many2one modal opened in full screen");
        // click on back button
        await testUtils.dom.click($(".modal").find(".modal-header .fa-arrow-left"));
        assert.strictEqual(window.scrollY, scrollPosition.top, "Should have scrolled back to 265 px vertically");
        assert.strictEqual(window.scrollX, scrollPosition.left, "Should be 0 px from left as it is");

        form.destroy();
    });

});

});
