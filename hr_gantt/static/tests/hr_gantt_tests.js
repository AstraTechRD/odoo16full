odoo.define('hr_gantt.Tests', function (require) {
    'use strict';

    const { createView } = require('web.test_utils');
    const HrGanttView = require('hr_gantt.GanttView');

    let initialDate = new Date(2018, 11, 20, 8, 0, 0);
    initialDate = new Date(initialDate.getTime() - initialDate.getTimezoneOffset() * 60 * 1000);

    QUnit.module('hr_gantt', {}, function () {
        QUnit.module('GanttView', {
            beforeEach: function () {
                this.data = {
                    tasks: {
                        fields: {
                            name: {string: 'Name', type: 'char'},
                            start: {string: 'Start Date', type: 'datetime'},
                            stop: {string: 'Stop Date', type: 'datetime'},
                            employee_id: {string: "Employee", type: 'many2one', relation: 'hr.employee'},
                            foo: {string: "Foo", type: 'char'},
                        },
                        records: [
                            {id: 1, name: 'Task 1', start: '2018-11-30 18:30:00', stop: '2018-12-31 18:29:59', employee_id: 11, foo: 'Foo 1'},
                            {id: 2, name: 'Task 2', start: '2018-12-17 11:30:00', stop: '2018-12-22 06:29:59', employee_id: 7, foo: 'Foo 2'},
                            {id: 3, name: 'Task 3', start: '2018-12-27 06:30:00', stop: '2019-01-03 06:29:59', employee_id: 23, foo: 'Foo 1'},
                            {id: 4, name: 'Task 4', start: '2018-12-19 18:30:00', stop: '2018-12-20 06:29:59', employee_id: 11, foo: 'Foo 3'}
                        ],
                    },
                    'hr.employee': {
                        fields: {},
                        records: [
                            {id: 11, name: "Mario"},
                            {id: 7, name: "Luigi"},
                            {id: 23, name: "Yoshi"},
                        ],
                    },
                };
            },
        });

        QUnit.test('hr gantt view not grouped', async function (assert) {
            assert.expect(1);

            const gantt = await createView({
                View: HrGanttView,
                model: 'tasks',
                data: this.data,
                arch: '<gantt date_start="start" date_stop="stop" />',
                viewOptions: {
                    initialDate: initialDate,
                },
            });

            assert.containsNone(gantt, '.o_standalone_avatar_employee',
                'should have 0 employee avatars');

            gantt.destroy();
        });

        QUnit.test('hr gantt view grouped by employee only', async function (assert) {
            assert.expect(1);

            const gantt = await createView({
                View: HrGanttView,
                model: 'tasks',
                data: this.data,
                arch: '<gantt date_start="start" date_stop="stop" />',
                viewOptions: {
                    initialDate: initialDate,
                },
                groupBy: ['employee_id'],
            });

            assert.containsN(gantt,
                '.o_gantt_row .o_gantt_row_sidebar .o_gantt_row_title .o_gantt_row_employee_avatar .o_standalone_avatar_employee',
                3, 'should have 3 employee avatars');

            gantt.destroy();
        });

        QUnit.test('hr gantt view grouped by employee > foo', async function (assert) {
            assert.expect(1);

            const gantt = await createView({
                View: HrGanttView,
                model: 'tasks',
                data: this.data,
                arch: '<gantt date_start="start" date_stop="stop" />',
                viewOptions: {
                    initialDate: initialDate,
                },
                groupBy: ['employee_id', 'foo'],
            });

            assert.containsN(gantt,
                '.o_gantt_row_group .o_gantt_row_sidebar .o_gantt_row_title .o_gantt_row_employee_avatar .o_standalone_avatar_employee',
                3, 'should have 3 employee avatars');

            gantt.destroy();
        });

        QUnit.test('hr gantt view grouped by foo > employee', async function (assert) {
            assert.expect(1);

            const gantt = await createView({
                View: HrGanttView,
                model: 'tasks',
                data: this.data,
                arch: '<gantt date_start="start" date_stop="stop" />',
                viewOptions: {
                    initialDate: initialDate,
                },
                groupBy: ['foo', 'employee_id'],
            });

            assert.containsN(gantt,
                '.o_gantt_row_nogroup .o_gantt_row_sidebar .o_gantt_row_title .o_gantt_row_employee_avatar .o_standalone_avatar_employee',
                4, 'should have 4 employee avatars');

            gantt.destroy();
        });
    });
});
