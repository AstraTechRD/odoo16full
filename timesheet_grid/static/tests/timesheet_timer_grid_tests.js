odoo.define('timesheet_grid.timesheet_grid_tests', function (require) {
"use strict";

var TimesheetTimerGridView = require('timesheet_grid.TimerGridView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;
const get_planned_and_worked_hours = function (args) {
    const ids = [...new Set(args[0].map(item => item.id))];
    const result = {};
    for (const id of ids) {
        result[id] = {
            'planned_hours': 8,
            'uom': 'hours',
            'worked_hours': 7,
        };
    }
    return result;
};

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            'analytic.line': {
                fields: {
                    project_id: {string: "Project", type: "many2one", relation: "project.project"},
                    task_id: {string: "Task", type: "many2one", relation: "project.task"},
                    date: {string: "Date", type: "date"},
                    unit_amount: {string: "Unit Amount", type: "float"},
                },
                records: [
                    {id: 1, project_id: 31, date: "2017-01-24", unit_amount: 2.5},
                    {id: 2, project_id: 31, task_id: 1, date: "2017-01-25", unit_amount: 2},
                    {id: 3, project_id: 31, task_id: 1, date: "2017-01-25", unit_amount: 5.5},
                    {id: 4, project_id: 31, task_id: 1, date: "2017-01-30", unit_amount: 10},
                    {id: 5, project_id: 142, task_id: 12, date: "2017-01-31", unit_amount: -3.5},
                ]
            },
            'project.project': {
                fields: {
                    name: {string: "Project Name", type: "char"},
                    allow_timesheets: {string: "Allow Timesheets", type: "boolean"},
                },
                records: [
                    {id: 31, display_name: "P1", allow_timesheets: true},
                    {id: 142, display_name: "Webocalypse Now", allow_timesheets: true},
                ],
                get_planned_and_worked_hours(args) {
                    return get_planned_and_worked_hours(args);
                }
            },
            'project.task': {
                fields: {
                    name: {string: "Task Name", type: "char"},
                    project_id: {string: "Project", type: "many2one", relation: "project.project"},
                },
                records: [
                    {id: 1, display_name: "BS task", project_id: 31},
                    {id: 12, display_name: "Another BS task", project_id: 142},
                    {id: 54, display_name: "yet another task", project_id: 142},
                ],
                get_planned_and_worked_hours(args) {
                    return get_planned_and_worked_hours(args);
                }
            },
        };
        this.arch = '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day" invisible="context.get(\'hide_second_button\')"/>' +
                        '<range name="year" string="Year" span="year" step="month"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                    '<button string="Action" type="action" name="action_name"/>' +
                '</grid>';
        this.context = {
            grid_range: 'week',
        };
        // patch debounce to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        _.debounce = _.identity;
    },
    afterEach: function () {
        // unpatch debounce
        _.debounce = this.underscoreDebounce;
    }
}, function () {
    QUnit.module('TimesheetTimerGridView');

    QUnit.test('basic timesheet timer grid view', async function (assert) {
        assert.expect(14);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(grid.$('table').length, "should have rendered a table");
        assert.ok(grid.$('.timesheet-timer').length, "should have rendered the timer header");
        assert.ok(grid.$('.btn_start_timer').length, "should have rendered the start timer button");
        assert.strictEqual(grid.$('button.btn_timer_line').length, 2, "should have rendered a start button before each line");
        assert.notOk(grid.$('button.btn_timer_line.red').length, "no line is running");

        // Start the timer
        await testUtils.dom.click(grid.$('.btn_start_timer'));
        await testUtils.nextTick();
        assert.notOk(grid.$('.btn_start_timer').length, "start timer button must disappear");
        assert.ok(grid.$('.input_timer').length, "should have rendered the timer");
        assert.ok(grid.$('.btn_stop_timer').length, "should have rendered the stop timer button");
        assert.ok(document.activeElement === grid.$('.btn_stop_timer').get(0), "stop button focused");
        assert.ok(grid.$('.timer_project_id').length, "should have rendered the project input");
        assert.notOk(grid.$('.timer_project_id.o_field_invalid').length, "project input must be show as valid");
        assert.ok(grid.$('.timer_task_id').length, "should have rendered the task input");

        // Try to stop timer, but as they are no project, it must fail, and timer continues to run
        await testUtils.dom.click(grid.$('.btn_stop_timer'));
        assert.ok(grid.$('.btn_stop_timer').length, "stop button must always be there");
        assert.ok(grid.$('.timer_project_id.o_field_invalid').length, "project input must be show as invalid");

        grid.destroy();
    });

    QUnit.test('Timer already running', async function (assert) {
        assert.expect(8);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve({
                        'id': 10,
                        'start': 5740, // 01:35:40
                        'project_id': 31,
                        'task_id': 1,
                        'description': 'Description',
                    });
                } else if (args.method === 'create') {
                    return Promise.resolve(24);
                } else if (args.method === 'action_add_time_to_timer') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.nextTick();
        assert.ok(grid.$('.btn_stop_timer').length, "should have rendered the stop timer button");
        assert.hasClass(grid.$('.btn_timer_line').eq(0), 'fa-play', "should have rendered the play timer button on first line");
        assert.doesNotHaveClass(grid.$('.btn_timer_line').eq(1), 'fa-play', "should have rendered the button on second line");
        assert.strictEqual(grid.$('.btn_timer_line').length, 2, "should have rendered the button on each line");
        assert.strictEqual(grid.$('.timer_project_id input').get(0).value, 'P1', "project is set");
        assert.strictEqual(grid.$('.timer_task_id input').get(0).value, 'BS task', "task is set");
        assert.strictEqual(grid.$('.input_description input').get(0).value, 'Description', "description is set");
        await testUtils.nextTick();
        assert.ok(grid.$('.input_timer').text().includes('01:35:4'), "timer is set");

        grid.destroy();
    });

    QUnit.test('stop running timer then restart new one', async function (assert) {
        assert.expect(9);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve({
                        'id': 10,
                        'start': 5740, // 01:35:40
                        'project_id': 31,
                        'task_id': 1,
                        'description': 'Description',
                    });
                } else if (args.method === 'create') {
                    return Promise.resolve(24);
                } else if (args.method === 'action_add_time_to_timer') {
                    return Promise.resolve();
                } else if (args.method === 'action_timer_stop') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.nextTick();
        await testUtils.dom.click(grid.$('.btn_stop_timer'));
        assert.notOk(grid.$('.btn_timer_line.fa-play').length, "No timer button line should be in play mode");
        assert.ok(document.activeElement === grid.$('.btn_start_timer').get(0), "start button focused");

        // We start a new timer (all fields must be empty)
        await testUtils.dom.click(grid.$('.btn_start_timer'));
        await testUtils.nextTick();
        assert.ok(document.activeElement === grid.$('.btn_stop_timer').get(0), "stop button focused");
        assert.ok(grid.$('.btn_stop_timer').length, "should have rendered the stop timer button");
        assert.notOk(grid.$('.btn_timer_line.fa-play').length, "No timer button line should be in play mode");
        assert.strictEqual(grid.$('.timer_project_id input').get(0).value, '', "project is reset");
        assert.strictEqual(grid.$('.timer_task_id input').get(0).value, '', "task is reset");
        assert.strictEqual(grid.$('.input_description input').get(0).value, '', "description is reset");
        await testUtils.nextTick();
        assert.ok(grid.$('.input_timer').text().includes('00:00:0'), "timer is reset");

        grid.destroy();
    });

    QUnit.test('drop running timer then restart new one', async function (assert) {
        assert.expect(7);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve({
                        'id': 10,
                        'start': 5740, // 01:35:40
                        'project_id': 31,
                        'task_id': 1,
                        'description': 'Description',
                    });
                } else if (args.method === 'create') {
                    return Promise.resolve(24);
                } else if (args.method === 'action_add_time_to_timer') {
                    return Promise.resolve();
                } else if (args.method === 'action_timer_unlink') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.nextTick();
        // We drop running timer with escape key press event
        await testUtils.dom.triggerEvent(grid.el, 'keydown', { key: 'Escape', target: {tagName: 'div'}});
        assert.notOk(grid.$('.btn_timer_line.fa-play').length, "No timer button line should be in play mode");

        // We start a new timer
        await testUtils.dom.click(grid.$('.btn_start_timer'));
        await testUtils.nextTick();
        assert.ok(grid.$('.btn_stop_timer').length, "should have rendered the stop timer button");
        assert.notOk(grid.$('.btn_timer_line.fa-play').length, "No timer button line should be in play mode");
        assert.strictEqual(grid.$('.timer_project_id input').get(0).value, '', "project is reset");
        assert.strictEqual(grid.$('.timer_task_id input').get(0).value, '', "task is reset");
        assert.strictEqual(grid.$('.input_description input').get(0).value, '', "description is reset");
        await testUtils.nextTick();
        assert.ok(grid.$('.input_timer').text().includes('00:00:0'), "timer is reset");

        grid.destroy();
    });

    QUnit.test('Start buttons with groupBy', async function (assert) {
        assert.expect(3);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(grid.$('button.btn_timer_line').length, "should have rendered a start button before each line");

        // If groupBy on timesheet, we can't launch timer from lines.
        await grid.update({groupBy: ["task_id"]});
        assert.notOk(grid.$('button.btn_timer_line').length, "shouldn't have rendered a start button before each line");

        await grid.update({groupBy: ["project_id"]});
        assert.ok(grid.$('button.btn_timer_line').length, "should have rendered a start button before each line");

        grid.destroy();
    });

    QUnit.test('Start button with shift', async function (assert) {
        assert.expect(8);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve();
                } else if (args.method === 'action_add_time_to_timesheet') {
                    this.data['analytic.line']['records'].push(
                        {id: 6, project_id: 31, task_id: false, date: "2017-01-25", unit_amount: 0.5},
                    )
                    return Promise.resolve(78);
                } else if (args.method === 'check_can_start_timer') {
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
        });
        // Before holding the shift button, the buttons before the lines are in the normal position.
        assert.strictEqual(grid.$('.timesheet-timer').text().indexOf('30'), -1, "should have rendered classic description");
        let characters = grid.$('button.btn_timer_line').text();
        assert.strictEqual(characters, characters.toLowerCase(), "All letters are lowercase");

        // Hold down the shift key, the buttons before the lines are in uppercase and the text changes.
        await testUtils.dom.triggerEvent(window, 'keydown', { key: 'Shift'});
        assert.ok(grid.$('.timesheet-timer').text().indexOf('30'), "should have rendered the text about time added");
        characters = grid.$('button.btn_timer_line').text();
        assert.strictEqual(characters, characters.toUpperCase(), "All letters are uppercase");

        await testUtils.dom.triggerEvent(grid.$('.btn_start_timer'), 'keydown', { key: 'b', which: '66'});
        await testUtils.dom.triggerEvent(grid.$('.btn_start_timer'), 'keydown', { key: 'b', which: '66'});
        await testUtils.dom.triggerEvent(grid.$('.btn_start_timer'), 'keydown', { key: 'b', which: '66'});
        await testUtils.nextTick();
        assert.strictEqual(grid.$('tbody tr:nth(1) td:nth(2)').text(), "1:30", "Time is correctly added");

        // Release the shift key and return to normal position.
        await testUtils.dom.triggerEvent(window, 'keyup', { key: 'Shift'});
        assert.strictEqual(grid.$('.timesheet-timer').text().indexOf('30'), -1, "should have rendered classic description");
        characters = grid.$('button.btn_timer_line').text();
        assert.strictEqual(characters, characters.toLowerCase(), "All letters are lowercase");

        // Start the timer, the shift key can no longer be used
        await testUtils.dom.click(grid.$('.btn_start_timer'));
        await testUtils.nextTick();
        await testUtils.dom.triggerEvent(grid.$('.btn_stop_timer'), 'keydown', { key: 'Shift'});
        characters = grid.$('button.btn_timer_line').text();
        assert.strictEqual(characters, characters.toLowerCase(), "All letters are lowercase");

        grid.destroy();
    });

    QUnit.test('Start timer from button line', async function (assert) {
        assert.expect(13);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve();
                } else if (args.method === 'create') {
                    return Promise.resolve(24);
                } else if (args.method === 'action_add_time_to_timer') {
                    return Promise.resolve();
                } else if (args.method === 'action_timer_stop') {
                    return Promise.resolve();
                } else if (args.method === 'check_can_start_timer') {
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.nextTick();
        // No timer is running. We click on button from line 1:
        //      -> start new timer for line 1
        await testUtils.dom.click(grid.$('button.btn_timer_line').get(0));
        assert.ok(grid.$('.btn_stop_timer').length, "should have rendered the stop timer button");
        assert.hasClass(grid.$('.btn_timer_line').eq(0), 'fa-play', "should have rendered the play timer button on first line");
        assert.doesNotHaveClass(grid.$('.btn_timer_line').eq(1), 'fa-play', "should have rendered the button on second line");
        assert.strictEqual(grid.$('.timer_project_id input').get(0).value, 'P1', "project is set");
        assert.strictEqual(grid.$('.timer_task_id input').get(0).value, 'BS task', "task is set");

        // timer linked to line 1 is running. We click on button from line 2:
        //      -> stop timer from line 1
        //      -> start new timer for line 2
        await testUtils.dom.click(grid.$('button.btn_timer_line').get(1));
        assert.ok(grid.$('.btn_stop_timer').length, "should have rendered the stop timer button");
        assert.hasClass(grid.$('.btn_timer_line').eq(1), 'fa-play', "should have rendered the play timer button on second line");
        assert.doesNotHaveClass(grid.$('.btn_timer_line').eq(0), 'fa-play', "should have rendered the button on first line");
        assert.strictEqual(grid.$('.timer_project_id input').get(0).value, 'P1', "project is set");
        assert.strictEqual(grid.$('.timer_task_id input').get(0).value, '', "no task is set");

        // timer linked to line 2 is running. We click on button from line 2:
        //      -> stop timer from line 2
        await testUtils.dom.click(grid.$('button.btn_timer_line').get(1));
        assert.ok(grid.$('.btn_start_timer').length, "should have rendered the start timer button");
        assert.notOk(grid.$('.btn_timer_line.red.fa-play').length, "no play button on lines (as no timer is running)");
        assert.strictEqual(grid.$('.btn_timer_line').length, 2, "should have rendered the button on each line");

        grid.destroy();
    });

    QUnit.test('Change description running timer', async function (assert) {
        assert.expect(2);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve({
                        'id': 10,
                        'start': 5740, // 01:35:40
                        'project_id': 31,
                        'task_id': 1,
                        'description': '/',
                    });
                } else if (args.method === 'change_description') {
                    assert.strictEqual(args.args[1], 'Description', 'New description is saved')
                    return Promise.resolve();
                } else if (args.method === 'action_timer_stop') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.nextTick();
        let descriptionInput = grid.$('.input_description input').get(0);
        await testUtils.fields.editInput(descriptionInput, 'Description');
        // When click on the enter button in input, timer must stop
        await testUtils.dom.triggerEvent(descriptionInput, 'keydown', { key: 'Enter'});
        assert.ok(grid.$('.btn_start_timer').length, "should have rendered the start timer button");

        grid.destroy();
    });

    QUnit.test('Edit timer manually', async function (assert) {
        assert.expect(8);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': false
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve({
                        'id': 10,
                        'start': 5740, // 01:35:40
                        'project_id': 31,
                        'task_id': 1,
                        'description': '/',
                    });
                } else if (args.method === 'action_add_time_to_timer') {
                    return Promise.resolve();
                } else if (args.method === 'get_rounded_time') {
                    return Promise.resolve(0.25); //00:15
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.nextTick();
        await testUtils.dom.click(grid.$('#display_timer'));
        assert.notOk(grid.$('#display_timer').length, "Span timer must disappear");
        let timerInput = grid.$('input.input_manual_time').get(0);
        assert.ok(timerInput, "Input timer must be rendered");
        assert.strictEqual(timerInput.value, '00:15', "should be the time returned by rounded function");
        await testUtils.fields.editInput(timerInput, 'abc');
        assert.hasClass(timerInput, 'o_field_invalid', "'abc' is not a valid time, the input must be invalid");
        await testUtils.fields.editInput(timerInput, '0:23');
        assert.doesNotHaveClass(timerInput, 'o_field_invalid', "'0:23' is a valid time, the input must not be invalid");
        await testUtils.dom.triggerEvent(timerInput, 'focusout');
        assert.notOk(grid.$('input.input_manual_time').length, "Input timer must disappear");
        assert.ok(grid.$('#display_timer').length, "Span timer must be rendered");
        await testUtils.nextTick();
        assert.ok(grid.$('#display_timer').text().includes('00:23:0'), "the timer must run from the value entered");

        grid.destroy();
    });

    QUnit.test('Timer with favorite project', async function (assert) {
        assert.expect(7);

        var grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': 31
                    });
                } else if (args.method === 'get_running_timer') {
                    return Promise.resolve();
                } else if (args.method === 'create') {
                    return Promise.resolve(24);
                } else if (args.method === 'action_add_time_to_timer') {
                    return Promise.resolve();
                } else if (args.method === 'action_change_project_task') {
                    assert.deepEqual(args.args, [[24], 31, 1], "check timesheet_id, project_id and task_id");
                    return Promise.resolve(24);
                } else if (args.method === 'name_search' && args.model === 'project.task') {
                    return Promise.resolve([[1, "BS task"]]);
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.nextTick();
        await testUtils.dom.click(grid.$('.btn_start_timer'));
        await testUtils.nextTick();
        // Project is already set, as they are a favorite project
        assert.strictEqual(grid.$('.timer_project_id input').get(0).value, 'P1', "favorite project is set");
        assert.strictEqual(grid.$('.timer_task_id input').get(0).value, '', "No task selected");
        assert.hasClass(grid.$('.btn_timer_line').eq(1), 'fa-play', "should have rendered the play timer button on second line");
        assert.doesNotHaveClass(grid.$('.btn_timer_line').eq(0), 'fa-play', "should have rendered the button on first line");
        await testUtils.fields.many2one.clickOpenDropdown('task_id');
        await testUtils.fields.many2one.clickHighlightedItem('task_id');
        assert.hasClass(grid.$('.btn_timer_line').eq(0), 'fa-play', "should have rendered the play timer button on line");
        assert.doesNotHaveClass(grid.$('.btn_timer_line').eq(1), 'fa-play', "should have rendered the button on second line");

        grid.destroy();
    });

    QUnit.test('Edit cell manually with shift key pressed', async function (assert) {
        assert.expect(4);

        const grid = await createView({
            View: TimesheetTimerGridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
            context: this.context,
            mockRPC: function (route, args) {
                if (args.method === 'get_timer_data') {
                    return Promise.resolve({
                        'step_timer': 30,
                        'favorite_project': 31
                    });
                } else if (args.method === 'search') {
                    return Promise.resolve([1, 2, 3, 4, 5]);
                } else if (args.method === 'adjust_grid') {
                    return Promise.resolve([]);
                }
                return this._super.apply(this, arguments);
            },
        });

        const $cell = grid.$('.o_grid_cell_container:eq(0)');
        const $div = $cell.find('div.o_grid_input');
        assert.doesNotHaveClass($div, 'o_has_error', "input should not show any error at start");

        await testUtils.dom.triggerEvent($(window)[0].$("body"), 'keydown', {key: 'Shift'});
        await testUtils.dom.triggerEvent($div, 'focus');
        const $input = $cell.find('input.o_grid_input');
        await testUtils.dom.triggerEvent($input, 'focus');
        document.execCommand('insertText', false, "0");
        document.execCommand('insertText', false, "4");
        assert.strictEqual($input.val(), "04",
            "val should be 04");
        await testUtils.dom.triggerEvent($input, 'keyup', {key: 'Shift'});
        document.execCommand('insertText', false, ":");
        await testUtils.dom.triggerEvent($input, 'keydown', {key: 'Shift'});
        document.execCommand('insertText', false, "3");
        document.execCommand('insertText', false, "0");
        await testUtils.dom.triggerEvent($input, 'keyup', {key: 'Shift'});
        assert.doesNotHaveClass($input, 'o_has_error',
            "input should not be formatted like there is an error");
        assert.strictEqual($input.val(), "04:30",
            "val should be 04:30");

        grid.destroy();
    });

});
});
