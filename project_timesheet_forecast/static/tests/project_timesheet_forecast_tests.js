odoo.define("project_timesheet_forecast.project_timesheet_forecast_tests", function (require) {
    "use strict";

    const ForecastTimesheetGanttView = require("forecast_timesheet.ForecastTimesheetGanttView");
    const testUtils = require("web.test_utils");

    const actualDate = new Date(2020, 6, 26, 8, 0, 0);
    const initialDate = new Date(
        actualDate.getTime() - actualDate.getTimezoneOffset() * 60 * 1000
    );
    const {createView} = testUtils;

    QUnit.module("Project Timesheet Forecast", {
        beforeEach() {
            this.data = {
                tasks: {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        name: {string: "Name", type: "char"},
                        start: {string: "Start Date", type: "datetime"},
                        stop: {string: "Stop Date", type: "datetime"},
                        time: {string: "Time", type: "float"},
                        effective_hours: {string: "Effective Hours", type: "float"},
                        planned_hours: {string: "Initially Planned Hours", type: "float"},
                        allocated_hours: {string: "Allocated Hours", type: "float"},
                        percentage_hours: {string: "Progress", type: "float"},
                        project_id: {string: 'Project', type: 'many2one', relation: 'projects'},
                        task_id: {string: 'Task', type: 'many2one', relation: 'stuffs'},
                        employee_id: {
                            string: "Assigned to",
                            type: "many2one",
                            relation: "employee",
                        },
                        active: {string: "active", type: "boolean", default: true},
                        allow_task_dependencies: { string: "Allow Task Dependencies", type: "boolean", default: false},
                        display_warning_dependency_in_gantt: { string: "Display Warning Dependency", type: "boolean", default: false},
                    },
                    records: [
                        {id: 1, name: 'Do what you gotta do', start: '2020-06-10 08:30:00', stop: '2020-06-10 12:30:00', 
                        project_id: 1, employee_id: 100, allocated_hours: 5, effective_hours: 0, percentage_hours: 0.0, planned_hours: 3, task_id: 1},
                        {id: 2, name: 'Or not', start: '2020-06-20 08:30:00', stop: '2020-06-20 10:30:00', 
                        project_id: 2, employee_id: 200, allocated_hours: 10, effective_hours: 2, percentage_hours: 20.0, planned_hours: 5, task_id: 2},
                        {id: 3, name: "Ain't Your Mama", start: '2020-06-21 08:30:00', stop: '2020-06-21 10:30:00',
                        project_id: 2, employee_id: 200, allocated_hours: 10, effective_hours: 0, percentage_hours: 0.0, planned_hours: 5},
                        {id: 4, name: "...", start: '2020-06-20 08:30:00', stop: '2020-06-20 10:30:00',
                        project_id: 2, employee_id: 200, effective_hours: 2, percentage_hours: 0.0, planned_hours: 5, task_id: 2},
                    ],
                },
                employee: {
                    fields: {
                        id: {string: "ID", type: "integer"},
                        name: {string: "Name", type: "char"},
                    },
                    records: [
                        {id: 100, name: "Richard"},
                        {id: 200, name: "Jesus"}
                    ]
                },
                projects: {
                    fields: {
                        id: {string: 'ID', type: 'integer'},
                        name: {string: 'Name', type: 'char'},
                    },
                    records: [
                        {id: 1, name: 'Project 1'},
                        {id: 2, name: 'Project 2'},
                    ],
                },
                stuffs: {
                    fields: {
                        id: {string: 'ID', type: 'integer'},
                        name: {string: 'Name', type: 'char'},
                    },
                    records: [
                        {id: 1, name: 'Do what you gotta do'},
                        {id: 2, name: 'Or not'},
                    ],
                },
            };
        },
    }, function () {

        QUnit.module("Progress Bar");

        QUnit.test('Check progress bar values', async function (assert) {
            assert.expect(7);

            const gantt = await createView({
                View: ForecastTimesheetGanttView,
                model: 'tasks',
                data: this.data,
                arch: '<gantt date_start="start" date_stop="stop" sample="0" progress="percentage_hours"/>',
                viewOptions: {
                    initialDate: initialDate,
                },
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/search_read') {
                        assert.strictEqual(args.model, 'tasks',
                            "should read on the correct model");
                        return Promise.resolve({
                            records: this.data.tasks.records
                        });

                    } else if (route === '/web/dataset/call_kw/tasks/read_group') {
                        throw Error("Should not call read_group when no groupby !");
                    }
                    return this._super.apply(this, arguments);
                },
                archs: {
                    'tasks,false,form': `
                        <form>
                            <field name="name"/>
                            <field name="start"/>
                            <field name="stop"/>
                            <field name="employee_id"/>
                            <field name="planned_hours"/>
                            <field name="effective_hours"/>
                            <field name="task_id"/>
                            <field name="percentage_hours"/>
                        </form>`,
                },
            });
            const pills = document.querySelectorAll(".o_gantt_pill");
            assert.strictEqual(pills[0].querySelector("span").dataset['progress'], "0%;", "The first task should have no progress");
            assert.strictEqual(pills[0].querySelector("span").getAttribute('style'), "width:0%;", "The style should reflect the data-progress value");
            assert.strictEqual(pills[1].querySelector("span").dataset['progress'], "20%;", "The second task should have 20% progress");
            assert.strictEqual(pills[1].querySelector("span").getAttribute('style'), "width:20%;", "The style should reflect the data-progress value");
            assert.strictEqual(pills[2].querySelector("span").dataset['progress'], "0%;", "The third task should have no progress");
            assert.strictEqual(pills[3].querySelector("span").dataset['progress'], "0%;", "The fourth task should have no progress");
            gantt.destroy();
        });
    });
});
