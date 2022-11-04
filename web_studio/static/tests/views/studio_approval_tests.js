/** @odoo-module */

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import {
    getFixture,
    patchWithCleanup,
    click,
    nextTick,
    makeDeferred,
} from "@web/../tests/helpers/utils";
import { session } from "@web/session";
import { registry } from "@web/core/registry";

const fakeStudioService = {
    start() {
        return {
            mode: null,
        };
    },
};

QUnit.module("Studio Approval", (hooks) => {
    let target;
    let serverData;

    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        bar: { string: "Bar", type: "boolean" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            int_field: 42,
                            bar: true,
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            int_field: 27,
                            bar: true,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
        registry.category("services").add("studio", fakeStudioService);
    });

    QUnit.test("approval components are synchronous", async (assert) => {
        const prom = makeDeferred();
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><button studio_approval="True" type="object" name="myMethod"/></form>`,
            async mockRPC(route, args) {
                if (args.method === "get_approval_spec") {
                    assert.step(args.method);
                    await prom;
                    return {
                        rules: [
                            {
                                id: 1,
                                group_id: [1, "Internal User"],
                                domain: false,
                                can_validate: true,
                                message: false,
                                exclusive_user: false,
                            },
                        ],
                        entries: [],
                        groups: [[1, "Internal User"]],
                    };
                }
            },
        });
        assert.verifySteps(["get_approval_spec"]);
        assert.containsOnce(target, "button .o_web_studio_approval .fa-circle-o-notch.fa-spin");
        prom.resolve();
        await nextTick();
        assert.containsNone(target, "button .o_web_studio_approval .fa-circle-o-notch.fa-spin");
        assert.containsOnce(target, "button .o_web_studio_approval .o_web_studio_approval_avatar");
    });

    QUnit.test("approval widget basic rendering", async function (assert) {
        assert.expect(14);

        patchWithCleanup(session, {
            uid: 42,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form string="Partners">
                <sheet>
                    <header>
                        <button type="object" name="someMethod" string="Apply Method" studio_approval="True"/>
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
                    <button type="object" name="anotherMethod"
                            string="Apply Second Method" studio_approval="True"/>
                </sheet>
            </form>`,
            resId: 2,
            mockRPC: function (route, args) {
                if (args.method === "get_approval_spec") {
                    assert.step("fetch_approval_spec");
                    return Promise.resolve({
                        rules: [
                            {
                                id: 1,
                                group_id: [1, "Internal User"],
                                domain: false,
                                can_validate: true,
                                message: false,
                                exclusive_user: false,
                            },
                        ],
                        entries: [],
                        groups: [[1, "Internal User"]],
                    });
                }
            },
        });

        // check that the widget was inserted on visible buttons only
        assert.containsOnce(target, 'button[name="someMethod"] .o_web_studio_approval');
        assert.containsOnce(target, "#visibleStat .o_web_studio_approval");
        assert.containsNone(target, "#invisibleStat .o_web_studio_approval");
        assert.containsOnce(target, 'button[name="anotherMethod"] .o_web_studio_approval');
        assert.containsNone(target, ".o_group .o_web_studio_approval");
        // should have fetched spec for exactly 3 buttons
        assert.verifySteps(["fetch_approval_spec", "fetch_approval_spec", "fetch_approval_spec"]);
        // display popover
        await click(target, 'button[name="someMethod"] .o_web_studio_approval');
        assert.containsOnce(target, ".o-approval-popover");
        const popover = target.querySelector(".o-approval-popover");
        assert.containsOnce(popover, ".o_web_studio_approval_no_entry");
        assert.containsOnce(popover, ".o_web_approval_approve");
        assert.containsOnce(popover, ".o_web_approval_reject");
        assert.containsNone(popover, ".o_web_approval_cancel");
    });

    QUnit.test("approval check", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
            resId: 2,
            mockRPC: function (route, args) {
                const rule = {
                    id: 1,
                    group_id: [1, "Internal User"],
                    domain: false,
                    can_validate: true,
                    message: false,
                    exclusive_user: false,
                };
                if (args.method === "get_approval_spec") {
                    assert.step("fetch_approval_spec");
                    return Promise.resolve({
                        rules: [rule],
                        entries: [],
                        groups: [[1, "Internal User"]],
                    });
                } else if (args.method === "check_approval") {
                    assert.step("attempt_action");
                    return Promise.resolve({
                        approved: false,
                        rules: [rule],
                        entries: [],
                    });
                } else if (args.method === "someMethod") {
                    /* the action of the button should not be
                    called, as the approval is refused! if this
                    code is traversed, the test *must* fail!
                    that's why it's not included in the expected count
                    or in the verifySteps call */
                    assert.step("should_not_happen!");
                }
            },
        });

        await click(target, "#mainButton");
        // first render, handle click, rerender after click
        assert.verifySteps(["fetch_approval_spec", "attempt_action", "fetch_approval_spec"]);
    });

    QUnit.test("approval widget basic flow", async function (assert) {
        assert.expect(5);

        patchWithCleanup(session, {
            uid: 42,
        });

        let hasValidatedRule;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
            resId: 2,
            mockRPC: function (route, args) {
                if (args.method === "get_approval_spec") {
                    const spec = {
                        rules: [
                            {
                                id: 1,
                                group_id: [1, "Internal User"],
                                domain: false,
                                can_validate: true,
                                message: false,
                                exclusive_user: false,
                            },
                        ],
                        entries: [],
                        groups: [[1, "Internal User"]],
                    };
                    if (hasValidatedRule !== undefined) {
                        spec.entries = [
                            {
                                id: 1,
                                approved: hasValidatedRule,
                                user_id: [42, "Some rando"],
                                write_date: "2020-04-07 12:43:48",
                                rule_id: [1, "someMethod/partner (Internal User)"],
                                model: "partner",
                                res_id: 2,
                            },
                        ];
                    }
                    return Promise.resolve(spec);
                } else if (args.method === "set_approval") {
                    hasValidatedRule = args.kwargs.approved;
                    assert.step(hasValidatedRule ? "approve_rule" : "reject_rule");
                    return Promise.resolve(true);
                } else if (args.method === "delete_approval") {
                    hasValidatedRule = undefined;
                    assert.step("delete_approval");
                    return Promise.resolve(true);
                }
            },
        });

        // display popover and validate a rule, then cancel, then reject
        await click(target, 'button[name="someMethod"] .o_web_studio_approval');
        assert.containsOnce(target, ".o_popover");
        await click(target, ".o_popover button.o_web_approval_approve");
        await nextTick();
        await click(target, ".o_popover button.o_web_approval_cancel");
        await click(target, ".o_popover button.o_web_approval_reject");
        assert.verifySteps(["approve_rule", "delete_approval", "reject_rule"]);
    });
});
