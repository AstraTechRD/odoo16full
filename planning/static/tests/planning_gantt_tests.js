odoo.define("planning.planning_gantt_tests.js", function (require) {
    "use strict";

    const Domain = require("web.Domain");
    const PlanningGanttView = require("planning.PlanningGanttView");
    const testUtils = require("web.test_utils");
    const { prepareWowlFormViewDialogs } = require("@web/../tests/views/helpers");
    const { patchTimeZone } = require("@web/../tests/helpers/utils");

    const actualDate = new Date(2018, 11, 20, 8, 0, 0);
    const initialDate = new Date(
        actualDate.getTime() - actualDate.getTimezoneOffset() * 60 * 1000
    );
    const { createView } = testUtils;

    QUnit.module("Planning", {
        beforeEach() {
            this.data = {
                task: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        start: { string: "Start Date", type: "datetime" },
                        stop: { string: "Stop Date", type: "datetime" },
                        time: { string: "Time", type: "float" },
                        resource_id: {
                            string: "Assigned to",
                            type: "many2one",
                            relation: "resource.resource",
                        },
                        department_id: {
                            string: "Department",
                            type: "many2one",
                            relation: "department",
                        },
                        role_id: {
                            string: "Role",
                            type: "many2one",
                            relation: "role",
                        },
                        active: { string: "active", type: "boolean", default: true },
                    },
                    records: [],
                },
                'resource.resource': {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
                department: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
                role: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [],
                },
            };
        },
    }, function () {

        QUnit.module("Gantt");

        QUnit.test("empty gantt view with sample data: send schedule", async function (assert) {
            assert.expect(3);

            this.data.task.records = [];

            const gantt = await createView({
                arch: `
                    <gantt date_start="start" date_stop="stop" sample="1"/>`,
                data: this.data,
                domain: Domain.FALSE_DOMAIN,
                groupBy: ["resource_id"],
                model: "task",
                View: PlanningGanttView,
                viewOptions: { initialDate },
            });

            testUtils.mock.intercept(gantt, 'call_service', (ev) => {
                if (ev.data.service === 'notification') {
                    const notification = ev.data.args[0];
                    assert.deepEqual(notification, {
                        type: 'danger',
                        message: "The shifts have already been published, or there are no shifts to publish.",
                    }, 'A danger notification should be displayed since there are no slots to send.');
                }
            }, true);

            assert.hasClass(gantt, "o_legacy_view_sample_data");
            assert.ok(gantt.$(".o_gantt_row").length > 2,
                'should contain at least two rows (the generic one, and at least one for sample data)');

            await testUtils.dom.click(gantt.el.querySelector(".btn.o_gantt_button_send_all"));

            gantt.destroy();
        });

        QUnit.test('add record in empty gantt with sample="1"', async function (assert) {
            assert.expect(7);

            this.data.task.records = [];

            const gantt = await createView({
                View: PlanningGanttView,
                model: 'task',
                data: this.data,
                arch: '<gantt date_start="start" date_stop="stop" sample="1"/>',
                viewOptions: {
                    initialDate: new Date(),
                },
                groupBy: ['resource_id'],
            });

            const views = {
                'task,false,form': `
                    <form>
                        <field name="name"/>
                        <field name="start"/>
                        <field name="stop"/>
                        <field name="resource_id"/>
                    </form>`,
            };
            await prepareWowlFormViewDialogs({ models: this.data, views });

            assert.hasClass(gantt, 'o_legacy_view_sample_data');
            assert.ok(gantt.$('.o_gantt_pill_wrapper').length > 0, "sample records should be displayed");
            const firstRow = gantt.$(".o_gantt_row:first")[0];
            assert.strictEqual(firstRow.innerText, "Open Shifts");
            assert.doesNotHaveClass(
                firstRow,
                "o_sample_data_disabled",
                "First row should not be disabled"
            );

            await testUtils.dom.triggerMouseEvent(gantt.$(`.o_gantt_row:first .o_gantt_cell:first .o_gantt_cell_add`), "click");
            await testUtils.fields.editInput($('.modal .modal-body .o_field_widget[name=name] input'), 'new task');
            await testUtils.modal.clickButton('Save & Close');

            assert.doesNotHaveClass(gantt, 'o_legacy_view_sample_data');
            assert.containsOnce(gantt, '.o_gantt_row');
            assert.containsOnce(gantt, '.o_gantt_pill_wrapper');

            gantt.destroy();
        });

        QUnit.test('open a dialog to add a new task', async function (assert) {
            assert.expect(4);

            patchTimeZone(0);

            const gantt = await createView({
                View: PlanningGanttView,
                model: 'task',
                data: this.data,
                arch: '<gantt default_scale="day" date_start="start" date_stop="stop"/>',
                archs: {
                    'task,false,form': '<form>' +
                            '<field name="name"/>' +
                            '<field name="start"/>' +
                            '<field name="stop"/>' +
                        '</form>',
                },
            });

            const views = {
                'task,false,form': `
                    <form>
                        <field name="name"/>
                        <field name="start"/>
                        <field name="stop"/>
                    </form>`,
            };
            const mockRPC = (route, args) => {
                if (args.method === 'onchange') {
                    const today = moment().startOf('date');
                    const todayStr = today.format("YYYY-MM-DD 23:59:59");
                    assert.strictEqual(args.kwargs.context.default_stop, todayStr, "default stop date should have 24 hours difference");
                }
            }
            await prepareWowlFormViewDialogs({ models: this.data, views }, mockRPC);

            await testUtils.dom.click(gantt.$el.find('.o_gantt_button_add'));
            // check that the dialog is opened with prefilled fields
            assert.containsOnce($('.o_dialog_container'), '.modal', 'There should be one modal opened');
            const today = moment().startOf('date');
            let todayStr = today.format("MM/DD/YYYY 00:00:00");
            assert.strictEqual($('.o_field_widget[name=start] .o_input').val(), todayStr,
                'the start date should be the start of the focus month');
            todayStr = today.format("MM/DD/YYYY 23:59:59");
            assert.strictEqual($('.o_field_widget[name=stop] .o_input').val(), todayStr,
                'the end date should be the end of the focus month');

            gantt.destroy();
        });

        QUnit.test("gantt view collapse and expand empty rows in multi groupby", async function (assert) {
            assert.expect(9);

            const gantt = await createView({
                View: PlanningGanttView,
                model: 'task',
                data: this.data,
                arch: '<gantt date_start="start" date_stop="stop"/>',
                archs: {
                    'task,false,form': `
                        <form>
                            <field name="name"/>
                            <field name="start"/>
                            <field name="stop"/>
                            <field name="resource_id"/>
                            <field name="role_id"/>
                            <field name="department_id"/>
                        </form>`,
                },
                viewOptions: {
                    initialDate: new Date(),
                },
                groupBy: ['department_id', 'role_id', 'resource_id'],
            });

            function getRow(index) {
                return gantt.el.querySelectorAll('.o_gantt_row_container > .row')[index];
            }
            assert.strictEqual(getRow(0).innerText.replace(/\s/, ''), 'Open Shifts',
                'should contain "Open Shifts" as a first group header for grouped by "Department"');
            assert.strictEqual(getRow(1).innerText.replace(/\s/, ''), 'Undefined Role',
                'should contain "Undefined Role" as a first group header for grouped by "Role"');
            assert.strictEqual(getRow(2).innerText, 'Open Shifts',
                'should contain "Open Shifts" as a first group header for grouped by "Employee"');

            await testUtils.dom.click(getRow(0));
            assert.doesNotHaveClass(getRow(0), 'open',
                "'Open Shift' Group Collapsed");
            await testUtils.dom.click(getRow(0));
            assert.hasClass(getRow(0), 'open',
                "'Open Shift' Group Expanded");
            assert.strictEqual(getRow(2).innerText, 'Open Shifts',
                'should contain "Open Shifts" as a first group header for grouped by "Employee"');
            await testUtils.dom.click(getRow(1));
            assert.doesNotHaveClass(getRow(1), 'open',
                "'Undefined Role' Sub Group Collapsed");
            await testUtils.dom.click(getRow(1));
            assert.hasClass(getRow(1), 'open',
                "'Undefined Role' Sub Group Expanded");
            assert.strictEqual(getRow(2).innerText, 'Open Shifts',
                'should contain "Open Shifts" as a first group header for grouped by "Employee"');

            gantt.destroy();
        });

    });
});
