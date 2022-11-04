odoo.define('web_studio.form_tests', function (require) {
    'use strict';

    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');
    require('web_studio.FormRenderer');
    require('web_studio.FormController');
    const { legacyExtraNextTick } = require("@web/../tests/helpers/utils");

    const createView = testUtils.createView;

    QUnit.module(
        'Studio',
        {
            beforeEach: function () {
                this.data = {
                    partner: {
                        fields: {
                            display_name: { string: 'Displayed name', type: 'char' },
                            int_field: { string: 'int_field', type: 'integer', sortable: true },
                            bar: { string: 'Bar', type: 'boolean' },
                        },
                        records: [
                            {
                                id: 1,
                                display_name: 'first record',
                                int_field: 42,
                                bar: true,
                            },
                            {
                                id: 2,
                                display_name: 'second record',
                                int_field: 27,
                                bar: true,
                            },
                        ],
                    },
                };
            },
        },
        function () {
            QUnit.module('Form Approvals');

            QUnit.test('approval widget basic rendering', async function (assert) {
                assert.expect(14);

                const form = await createView({
                    View: FormView,
                    model: 'partner',
                    data: this.data,
                    debug: true, // need to be in the viewport because of popover
                    arch: `<form string="Partners">
                        <sheet>
                            <header>
                                <button type="object=" name="someMethod" string="Apply Method" studio_approval="True"/>
                            </header>
                            <div name="button_box">
                                <button class="oe_stat_button" studio_approval="True" id="visibleStat">
                                    <field name="int_field"/>
                                </button>
                                <button class="oe_stat_button" studio_approval="True"
                                        attrs='{"invisible": [["bar", "=", true]]}' id="invisibleStat">
                                    <field name="bar"/>
                                </button>
                            </div>
                            <group>
                                <group style="background-color: red">
                                    <field name="display_name" studio_approval="True"/>
                                    <field name="bar"/>
                                    <field name="int_field"/>
                                </group>
                            </group>
                            <button type="object=" name="anotherMethod"
                                    string="Apply Second Method" studio_approval="True"/>
                        </sheet>
                    </form>`,
                    res_id: 2,
                    mockRPC: function (route, args) {
                        if (args.method === 'get_approval_spec') {
                            assert.step('fetch_approval_spec');
                            return Promise.resolve({
                                rules: [
                                    {
                                        id: 1,
                                        group_id: [1, 'Internal User'],
                                        domain: false,
                                        can_validate: true,
                                        message: false,
                                        exclusive_user: false,
                                    },
                                ],
                                entries: [],
                                groups: [[1, 'Internal User']],
                            });
                        }
                        return this._super(route, args);
                    },
                    session: { uid: 42 },
                });

                await legacyExtraNextTick(); // wait for the approval button (owl) to render

                // check that the widget was inserted on visible buttons only
                assert.containsOnce(form, 'button[name="someMethod"] .o_web_studio_approval');
                assert.containsOnce(form, '#visibleStat .o_web_studio_approval');
                assert.containsNone(form, '#invisibleStat .o_web_studio_approval');
                assert.containsOnce(form, 'button[name="anotherMethod"] .o_web_studio_approval');
                assert.containsNone(form, '.o_group .o_web_studio_approval');
                // should have fetched spec for exactly 3 buttons
                assert.verifySteps(['fetch_approval_spec', 'fetch_approval_spec', 'fetch_approval_spec']);
                // display popover
                await testUtils.dom.click('button[name="someMethod"] .o_web_studio_approval');
                assert.containsOnce($(document), '.o_popover');
                const popover = $(document).find('.o_popover');
                assert.containsOnce(popover, '.o_web_studio_approval_no_entry');
                assert.containsOnce(popover, '.o_web_approval_approve');
                assert.containsOnce(popover, '.o_web_approval_reject');
                assert.containsNone(popover, '.o_web_approval_cancel');

                form.destroy();
            });

            QUnit.test('approval check', async function (assert) {
                assert.expect(4);

                const form = await createView({
                    View: FormView,
                    model: 'partner',
                    data: this.data,
                    arch: `<form string="Partners">
                        <sheet>
                            <header>
                                <button type="object" id="mainButton" name="someMethod"
                                         string="Apply Method" studio_approval="True"/>
                            </header>
                            <group>
                                <group style="background-color: red">
                                    <field name="display_name"/>
                                    <field name="bar"/>
                                    <field name="int_field"/>
                                </group>
                            </group>
                        </sheet>
                    </form>`,
                    res_id: 2,
                    mockRPC: function (route, args) {
                        const rule = {
                            id: 1,
                            group_id: [1, 'Internal User'],
                            domain: false,
                            can_validate: true,
                            message: false,
                            exclusive_user: false,
                        };
                        if (args.method === 'get_approval_spec') {
                            assert.step('fetch_approval_spec');
                            return Promise.resolve({
                                rules: [rule],
                                entries: [],
                                groups: [[1, 'Internal User']],
                            });
                        } else if (args.method === 'check_approval') {
                            assert.step('attempt_action');
                            return Promise.resolve({
                                approved: false,
                                rules: [rule],
                                entries: [],
                            });
                        } else if (args.method === 'someMethod') {
                            /* the action of the button should not be
                        called, as the approval is refused! if this
                        code is traversed, the test *must* fail!
                        that's why it's not included in the expected count
                        or in the verifySteps call */
                            assert.step('should_not_happen!');
                        }
                        return this._super(route, args);
                    },
                });

                await testUtils.dom.click('#mainButton');
                // first render, handle click, rerender after click
                assert.verifySteps(['fetch_approval_spec', 'attempt_action', 'fetch_approval_spec']);

                form.destroy();
            });

            QUnit.test('approval widget basic flow', async function (assert) {
                assert.expect(5);

                let hasValidatedRule;

                const form = await createView({
                    View: FormView,
                    model: 'partner',
                    data: this.data,
                    debug: true, // need to be in the viewport because of popover
                    arch: `<form string="Partners">
                        <sheet>
                            <header>
                                <button type="object=" name="someMethod" string="Apply Method" studio_approval="True"/>
                            </header>
                            <group>
                                <group style="background-color: red">
                                    <field name="display_name"/>
                                    <field name="bar"/>
                                    <field name="int_field"/>
                                </group>
                            </group>
                        </sheet>
                    </form>`,
                    res_id: 2,
                    mockRPC: function (route, args) {
                        if (args.method === 'get_approval_spec') {
                            const spec = {
                                rules: [
                                    {
                                        id: 1,
                                        group_id: [1, 'Internal User'],
                                        domain: false,
                                        can_validate: true,
                                        message: false,
                                        exclusive_user: false,
                                    },
                                ],
                                entries: [],
                                groups: [[1, 'Internal User']],
                            };
                            if (hasValidatedRule !== undefined) {
                                spec.entries = [
                                    {
                                        id: 1,
                                        approved: hasValidatedRule,
                                        user_id: [42, 'Some rando'],
                                        write_date: '2020-04-07 12:43:48',
                                        rule_id: [1, 'someMethod/partner (Internal User)'],
                                        model: 'partner',
                                        res_id: 2,
                                    },
                                ];
                            }
                            return Promise.resolve(spec);
                        } else if (args.method === 'set_approval') {
                            hasValidatedRule = args.kwargs.approved;
                            assert.step(hasValidatedRule ? 'approve_rule' : 'reject_rule');
                            return Promise.resolve(true);
                        } else if (args.method === 'delete_approval') {
                            hasValidatedRule = undefined;
                            assert.step('delete_approval');
                            return Promise.resolve(true);
                        }
                        return this._super(route, args);
                    },
                    session: { uid: 42 },
                });

                await legacyExtraNextTick(); // wait for the approval button (owl) to render

                // display popover and validate a rule, then cancel, then reject
                await testUtils.dom.click('button[name="someMethod"] .o_web_studio_approval');
                assert.containsOnce($(document), '.o_popover');
                await testUtils.dom.click('.o_popover button.o_web_approval_approve');
                await testUtils.dom.click('.o_popover button.o_web_approval_cancel');
                await testUtils.dom.click('.o_popover button.o_web_approval_reject');
                assert.verifySteps(['approve_rule', 'delete_approval', 'reject_rule']);

                form.destroy();
            });
        }
    );
});
