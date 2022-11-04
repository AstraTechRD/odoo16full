/** @odoo-module **/

import { createView } from "web.test_utils";
import TaskGanttView from '@project_enterprise/js/task_gantt_view';

const actualDate = new Date(2020, 5, 22, 8, 0, 0);
const initialDate = new Date(actualDate.getTime() - actualDate.getTimezoneOffset() * 60 * 1000);

const ganttViewParams = {
    arch: `<gantt date_start="start" date_stop="stop" progress="progress"/>`,
    model: "task",
    View: TaskGanttView,
    viewOptions: { initialDate },
};

QUnit.module("Views > GanttView > TaskGantt", {
    beforeEach() {
        ganttViewParams.data = {
            task: {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Name", type: "char" },
                    progress: { string: "progress", type: "float" },
                    start: { string: "Start Date", type: "datetime" },
                    stop: { string: "Start Date", type: "datetime" },
                    user_id: { string: "Assigned to", type: "many2one", relation: "users" },
                    allow_timesheets: { string: "Allow timeshet", type: "boolean" },
                    project_id: {
                        string: "Project",
                        type: "many2one",
                        relation: "project",
                    },
                },
                records: [
                    {
                        id: 1,
                        name: "Blop",
                        start: "2020-06-14 08:00:00",
                        stop: "2020-06-24 08:00:00",
                        user_id: 100,
                        progress: 50.00,
                        allow_timesheets: true,
                        project_id: 1,
                    },
                    {
                        id: 2,
                        name: "Yop",
                        start: "2020-06-02 08:00:00",
                        stop: "2020-06-12 08:00:00",
                        user_id: 101, progress: 0,
                        allow_timesheets: true,
                        project_id: 1,
                    },
                ],
            },
            users: {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 100, name: "Jane Doe" },
                    { id: 101, name: "John Doe" },
                ],
            },
            project: {
                fields: {
                    id: { string: "ID", type: "integer" },
                    name: { string: "Name", type: "char" },
                },
                records: [{ id: 1, name: "My Project" }],
            },
        };
    },
});

QUnit.test("Check progress bar values", async (assert) => {
    assert.expect(5);
    ganttViewParams.mockRPC = function (route, args) {
        if (route === '/web/dataset/search_read') {
            assert.strictEqual(args.model, 'task',
                "should read on the correct model");
            return Promise.resolve({
                records: this.data.task.records
            });
        } else {
            if (args.method === 'search_milestone_from_task') {
                return Promise.resolve([]);
            }
            return this._super.apply(this, arguments);
        }
    };
    ganttViewParams.archs = {
        'tasks,false,form': `
            <form>
                <field name="name"/>
                <field name="start"/>
                <field name="stop"/>
            </form>`,
    };
    const gantt = await createView(ganttViewParams);
    const pills = document.querySelectorAll(".o_gantt_pill");
    assert.strictEqual(pills[0].querySelector("span").dataset['progress'], "0%;", "The first task should have no progress");
    assert.strictEqual(pills[0].querySelector("span").getAttribute('style'), "width:0%;", "The style should reflect the data-progress value");
    assert.strictEqual(pills[1].querySelector("span").dataset['progress'], "50%;", "The second task should have 50% progress");
    assert.strictEqual(pills[1].querySelector("span").getAttribute('style'), "width:50%;", "The style should reflect the data-progress value");
    gantt.destroy();
});
