/** @odoo-module **/

import { click, getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;

QUnit.module("Planning.planning_calendar_tests", ({ beforeEach }) => {
    beforeEach(() => {
        patchDate(2021, 5, 22, 8, 0, 0);
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.test("planning calendar view: copy previous week", async function (assert) {
        assert.expect(4);
        const serverData = {
            models: {
                "planning.slot": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Note", type: "text" },
                        color: { string: "Color", type: "integer" },
                        display_name: { string: "Name", type: "char" },
                        start: { string: "Start Date", type: "datetime" },
                        stop: { string: "Stop Date", type: "datetime" },
                        resource_id: { string: "Assigned to", type: "many2one", relation: "resource.resource" },
                        role_id: { string: "Role", type: "many2one", relation: "role" },
                        state: {
                            string: "State",
                            type: "selection",
                            selection: [
                                ["draft", "Draft"],
                                ["published", "Published"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            name: "First Record",
                            start: moment().format("YYYY-MM-DD HH:00:00"),
                            stop: moment().add(4, "hours").format("YYYY-MM-DD HH:00:00"),
                            resource_id: 1,
                            color: 7,
                            role_id: 1,
                            state: "draft",
                        },
                        {
                            id: 2,
                            name: "Second Record",
                            start: moment().add(2, "days").format("YYYY-MM-DD HH:00:00"),
                            stop: moment().add(2, "days").add(4, "hours").format("YYYY-MM-DD HH:00:00"),
                            resource_id: 2,
                            color: 9,
                            role_id: 2,
                            state: "published",
                        },
                    ],
                    methods: {
                        check_access_rights: () => Promise.resolve(true),
                    },
                },
                "resource.resource": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "Chaganlal" },
                        { id: 2, name: "Maganlal" },
                    ],
                },
                role: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        color: { string: "Color", type: "integer" },
                    },
                    records: [
                        { id: 1, name: "JavaScript Developer", color: 1 },
                        { id: 2, name: "Functional Consultant", color: 2 },
                    ],
                },
            },
            views: {},
        };

        const calendar = await makeView({
            type: "calendar",
            resModel: "planning.slot",
            serverData,
            arch: `<calendar class="o_planning_calendar_test"
                    event_open_popup="true"
                    date_start="start"
                    date_stop="stop"
                    color="color"
                    mode="week"
                    js_class="planning_calendar">
                        <field name="resource_id" />
                        <field name="role_id" filters="1" color="color"/>
                        <field name="state"/>
                </calendar>`,
            mockRPC: function (route, args) {
                if (args.method === "action_copy_previous_week") {
                    assert.step("copy_previous_week()");
                    return Promise.resolve({});
                }
            },
        });

        patchWithCleanup(calendar.env.services.action, {
            async doAction(action) {
                assert.deepEqual(
                    action,
                    "planning.planning_send_action",
                    "should open 'Send Planning By Email' form view"
                );
            },
        });

        await click(target.querySelector(".o_button_copy_previous_week"));
        assert.verifySteps(["copy_previous_week()"], "verify action_copy_previous_week() invoked.");

        // deselect "Maganlal" from Assigned to
        await click(target.querySelector(".o_calendar_filter_item[data-value='2'] > input"));
        assert.containsN(target, ".fc-event", 1, "should display 1 events on the week");

        await click(target.querySelector(".o_button_send_all"));
    });
});
