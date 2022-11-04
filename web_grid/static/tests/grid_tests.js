odoo.define('web_grid.grid_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var GridView = require('web_grid.GridView');
var testUtils = require('web.test_utils');

const cpHelpers = require('@web/../tests/search/helpers');
var createView = testUtils.createView;
const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
const {
    clickDropdown,
    clickOpenedDropdownItem,
    editInput,
    getFixture,
    patchWithCleanup,
} = require("@web/../tests/helpers/utils");
const { browser } = require("@web/core/browser/browser");
const { prepareWowlFormViewDialogs } = require("@web/../tests/views/helpers");

QUnit.module('LegacyViews', {
    beforeEach: function () {
        this.data = {
            'analytic.line': {
                fields: {
                    project_id: {string: "Project", type: "many2one", relation: "project"},
                    task_id: {string: "Task", type: "many2one", relation: "task"},
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
            project: {
                fields: {
                    name: {string: "Project Name", type: "char"}
                },
                records: [
                    {id: 31, display_name: "P1"},
                    {id: 142, display_name: "Webocalypse Now"},
                ]
            },
            task: {
                fields: {
                    name: {string: "Task Name", type: "char"},
                    project_id: {string: "Project", type: "many2one", relation: "project"},
                },
                records: [
                    {id: 1, display_name: "BS task", project_id: 31},
                    {id: 12, display_name: "Another BS task", project_id: 142},
                    {id: 54, display_name: "yet another task", project_id: 142},
                ]
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
        this.archs = {
            'analytic.line,23,form': '<form string="Add a line"><group><group>' +
                                  '<field name="project_id"/>' +
                                  '<field name="task_id"/>' +
                                  '<field name="date"/>' +
                                  '<field name="unit_amount" string="Time spent"/>' +
                                '</group></group></form>',
        };
    }
}, function () {
    QUnit.module('GridView (legacy)');

    QUnit.test('basic grid view', async function (assert) {
        assert.expect(18);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            mockRPC: function (route) {
                if (route === 'some-image') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });


        assert.ok(grid.$('table').length, "should have rendered a table");
        assert.containsN(grid, 'div.o_grid_cell_container', 14,
            "should have 14 cells");
        assert.strictEqual(grid.$('div.o_grid_input:contains(2:30)').length, 1,
            "should have correctly parsed a float_time");

        var cell = grid.$('div.o_grid_input:contains(2:30)').get(0);
        cell.focus();
        cell.click();

        assert.strictEqual(grid.$('div.o_grid_input:contains(0:00)').length, 12,
            "should have correctly parsed another float_time");

        assert.ok(grid.$buttons.find('button.grid_arrow_previous').is(':visible'),
            "previous button should be visible");
        assert.hasClass(grid.$buttons.find('button.grid_arrow_range[data-name="week"]'),'active',
            "current range is shown as active");

        assert.strictEqual(grid.$('tfoot td:contains(2:30)').length, 1, "should display total in a column");
        assert.strictEqual(grid.$('tfoot td.o_grid_cell_null:contains(0:00)').length, 5, "should display totals, even if 0");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));
        assert.ok(grid.$('div.o_grid_cell_container').length, "should not have any cells");
        assert.ok(grid.$('th div:contains(P1)').length,
            "should have rendered a cell with project name");
        assert.ok(grid.$('th div:contains(BS task)').length,
            "should have rendered a cell with task name");
        assert.notOk(grid.$('.o_grid_nocontent_container p:contains(Add projects and tasks)').length,
            "should not have rendered a no content helper");
        assert.hasClass(grid.$('tbody tr:eq(0) td:eq(1) .o_grid_input'), 'text-danger',
            "should have text-danger class on negative value cell");
        assert.hasClass(grid.$('tbody tr:eq(0) td.o_grid_total'), 'text-danger',
            "should have text-danger class on total column");
        assert.hasClass(grid.$('tfoot tr:eq(0) td:eq(2)'), 'text-danger',
            "should have text-danger class on footer total");

        assert.notOk(grid.$('td.o_grid_current').length, "should not have any cell marked current");
        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));

        assert.notOk(grid.$('div.o_grid_cell_container').length, "should not have any cell");

        var zeroTd = 0;
        grid.$('tfoot td').each(function () {
            if ($(this).text() === '0:00') {
                zeroTd++;
            }
        });
        assert.strictEqual(zeroTd, 8, "8 totals cells be equal to 0");
        grid.destroy();
    });

    QUnit.test('basic grouped grid view', async function (assert) {
        assert.expect(27);
        let nbReadGrid = 0;

        this.data['analytic.line'].records.push(
            {id: 6, project_id: 142, task_id: 12, date: "2017-01-31", unit_amount: 3.5},
        );

        this.arch = `<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid">
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`;

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            mockRPC: function (route, args) {
                if (route === 'some-image') {
                    return Promise.resolve();
                }
                else if (args.method === 'read_grid_grouped') {
                    if (nbReadGrid === 0) {
                        assert.deepEqual(args.kwargs.row_fields, ["task_id"],
                            "should have right row_fields");
                        assert.strictEqual(args.kwargs.col_field, "date",
                            "should have right col_field");
                        assert.strictEqual(args.kwargs.cell_field, "unit_amount",
                            "should have right cell_field");
                        assert.strictEqual(args.kwargs.section_field, "project_id",
                            "should have right section_field");
                    }
                    nbReadGrid++;
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.ok(grid.$('table').length, "should have rendered a table");
        assert.strictEqual(nbReadGrid, 1, "should have read_grid_grouped called once");
        assert.containsN(grid, '.o_grid_section', 2, "should have one section by project");

        // first section
        assert.strictEqual(grid.$('.o_grid_section:eq(0) th:contains(P1)').length, 1,
            "first section should be for project P1");
        assert.strictEqual(grid.$('.o_grid_section:eq(0) div.o_grid_cell_container').length, 14,
            "first section should have 14 cells");
        assert.strictEqual(grid.$('.o_grid_section:eq(0) th:contains(None)').length, 1,
            "first section should have a row without task");
        assert.strictEqual(grid.$('.o_grid_section:eq(0) th:contains(BS task)').length, 1,
            "first section should have a row for BS task");

        assert.strictEqual(grid.$('.o_grid_section:eq(0) tr:eq(2) div.o_grid_input:contains(2:30)').length, 1,
            "should have correctly parsed a float_time for cell without task");
        assert.strictEqual(grid.$('.o_grid_section:eq(0) div.o_grid_input:contains(0:00)').length, 12,
            "should have correctly parsed another float_time");

        // second section
        assert.strictEqual(grid.$('.o_grid_section:eq(1) th:contains(Webocalypse Now)').length, 1,
            "second section should be for project Webocalypse Now");
        assert.strictEqual(grid.$('.o_grid_section:eq(1) th:contains(Another BS task)').length, 0,
            "first section should be empty");
        assert.strictEqual(grid.$('.o_grid_section:eq(1) div.o_grid_cell_container').length, 0,
            "second section should be empty");

        assert.ok(grid.$buttons.find('button.grid_arrow_previous').is(':visible'),
            "previous button should be visible");
        assert.hasClass(grid.$buttons.find('button.grid_arrow_range[data-name="week"]'),'active',
            "current range is shown as active");

        assert.strictEqual(grid.$('tfoot td:contains(2:30)').length, 1, "should display total in a column");
        assert.strictEqual(grid.$('tfoot td.o_grid_cell_null:contains(0:00)').length, 5, "should display totals, even if 0");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));

        assert.strictEqual(nbReadGrid, 2, "should have read_grid_grouped called again");

        assert.ok(grid.$('div.o_grid_cell_container').length, "should not have any cells");
        assert.ok(grid.$('th:contains(P1)').length,
            "should have rendered a cell with project name");
        assert.ok(grid.$('th div:contains(BS task)').length,
            "should have rendered a cell with task name");
        assert.strictEqual(grid.$('.o_grid_section:eq(1) th:contains(Another BS task)').length, 1,
            "first section should have a row for Another BS task");
        assert.strictEqual(grid.$('.o_grid_section:eq(1) div.o_grid_cell_container').length, 7,
            "second section should have 7 cells");
        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));

        assert.containsNone(grid, '.o_grid_nocontent_container',
            "should not have rendered a no content helper in grouped");
        grid.destroy();
    });

    QUnit.test('grouped grid view with no data', async function (assert) {
        assert.expect(5);

        this.data['analytic.line'].records = [];

        this.arch = '<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid">' +
                '<field name="project_id" type="row" section="1"/>' +
                '<field name="task_id" type="row"/>' +
                '<field name="date" type="col">' +
                    '<range name="week" string="Week" span="week" step="day"/>' +
                    '<range name="month" string="Month" span="month" step="day"/>' +
                '</field>' +
                '<field name="unit_amount" type="measure" widget="float_time"/>' +
            '</grid>';

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
        });

        assert.isVisible(grid.$('.o_control_panel .grid_arrow_previous'));
        assert.isVisible(grid.$('.o_control_panel .grid_arrow_next'));
        assert.containsOnce(grid, '.o_view_grid .o_grid_section');
        assert.containsN(grid, '.o_view_grid thead th', 9); // title + 7 days + total
        assert.strictEqual(grid.el.querySelectorAll('.o_grid_padding').length, 4, 'should have 4 empty rows in table');

        grid.destroy();
    });

    QUnit.test('load and reload a grid view with favorite search', async function (assert) {
        assert.expect(4);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet By Project">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            groupBy: ["task_id", "project_id"], // user-set default search view
            currentDate: "2017-01-25",
        });

        assert.strictEqual(grid.$('tr:eq(1) th').text(), 'BS taskP1',
            "GroupBy should have been taken into account when loading the view."
        );
        assert.strictEqual(grid.$('tr:eq(2) th').text(), 'P1',
            "GroupBy should have been taken into account when loading the view."
        );

        await testUtils.dom.click(grid.$buttons.find('.grid_arrow_next'));

        assert.strictEqual(grid.$('tr:eq(1) th').text(), 'Another BS taskWebocalypse Now',
            "GroupBy should have been kept when clicking the pager."
        );
        assert.strictEqual(grid.$('tr:eq(2) th').text(), 'BS taskP1',
            "GroupBy should have been kept when clicking the pager."
        );

        grid.destroy();
    });

    QUnit.test('groupBy a string is supported', async function (assert) {
        // groupBy could be a single "field" instead of an Array of strings
        assert.expect(4);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet By Project">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            groupBy: "task_id",
            currentDate: "2017-01-25",
        });

        assert.strictEqual(grid.$('tr:eq(1) th').text(), 'BS task',
            "GroupBy should have been taken into account when loading the view."
        );
        assert.strictEqual(grid.$('tr:eq(2) th').text(), 'None',
            "GroupBy should have been taken into account when loading the view."
        );

        await testUtils.dom.click(grid.$buttons.find('.grid_arrow_next'));

        assert.strictEqual(grid.$('tr:eq(1) th').text(), 'Another BS task',
            "GroupBy should have been kept when clicking the pager."
        );
        assert.strictEqual(grid.$('tr:eq(2) th').text(), 'BS task',
            "GroupBy should have been kept when clicking the pager."
        );

        grid.destroy();
    });

    QUnit.test('groupBy a date with groupby function', async function (assert) {
        assert.expect(1);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet By Project">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            groupBy: "date:month",
            currentDate: "2017-01-25",
        });

        assert.strictEqual(grid.$('tbody tr:first th').text(), 'January 2017',
            "groupBy should have been taken into account when loading the view"
        );

        grid.destroy();
    });

    QUnit.test('Removing groupBy defaults to initial groupings', async function (assert) {
        assert.expect(5);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet By Project">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            groupBy: ["task_id", "project_id"],
            currentDate: "2017-01-25",
        });

        assert.strictEqual(grid.$('tr:eq(1) th').text(), 'BS taskP1',
            "GroupBy should have been taken into account when loading the view."
        );
        assert.strictEqual(grid.$('tr:eq(2) th').text(), 'P1',
            "GroupBy should have been taken into account when loading the view."
        );

        await grid.update({groupBy: []});

        assert.strictEqual(grid.$('tr:eq(1) th').text(), 'P1',
            "Should be grouped by default (Project > Task)."
        );
        assert.strictEqual(grid.$('tr:eq(2) th').text(), 'BS task',
            "Should be grouped by default (Project > Task)."
        );
        assert.strictEqual(grid.$('tr:eq(3) th').text(), 'None',
            "Should be grouped by default (Project > Task)."
        );

        grid.destroy();
    });

    QUnit.test('DOM keys are unique', async function (assert) {
        assert.expect(8);

        var line_records = [
                {id: 12, project_id: 142, date: "2017-01-17", unit_amount: 0},
                {id: 1, project_id: 31, date: "2017-01-24", unit_amount: 2.5},
                {id: 3, project_id: 143, date: "2017-01-25", unit_amount: 5.5},
                {id: 2, project_id: 33, date: "2017-01-25", unit_amount: 2},
                {id: 4, project_id: 143, date: "2017-01-18", unit_amount: 0},
                {id: 5, project_id: 142, date: "2017-01-18", unit_amount: 0},
                {id: 10, project_id: 31, date: "2017-01-18", unit_amount: 0},
                {id: 22, project_id: 33, date: "2017-01-19", unit_amount: 0},
                {id: 21, project_id: 99, date: "2017-01-19", unit_amount: 0},
        ];
        var project_records = [
                {id: 31, display_name: "Rem"},
                {id: 33, display_name: "Rer"},
                {id: 142, display_name: "Sas"},
                {id: 143, display_name: "Sassy"},
                {id: 99, display_name: "Sar"},
        ];
        this.data.project.records = project_records;
        this.data['analytic.line'].records = line_records;

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
        });
        assert.strictEqual(grid.$('tbody th:first').text(), "Rer", "Should be equal.");
        assert.strictEqual(grid.$('tbody th:eq(1)').text(), "Sassy", "Should be equal.");
        assert.strictEqual(grid.$('tbody th:eq(2)').text(), "Rem", "Should be equal.");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_previous'));
        assert.strictEqual(grid.$('tbody th:first').text(), "Sar", "Should be equal.");
        assert.strictEqual(grid.$('tbody th:eq(1)').text(), "Rer", "Should be equal.");
        assert.strictEqual(grid.$('tbody th:eq(2)').text(), "Rem", "Should be equal.");
        assert.strictEqual(grid.$('tbody th:eq(3)').text(), "Sassy", "Should be equal.");
        assert.strictEqual(grid.$('tbody th:eq(4)').text(), "Sas", "Should be equal.");

        grid.destroy();
    });

    QUnit.test('group by non-relational field', async function (assert) {
        assert.expect(1);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
        });

        await grid.update({groupBy: ["date"]});
        assert.strictEqual(grid.$('tbody th:first').text(),
                           "January 2017",
                           "Should be equal.");
        grid.destroy();
    });

    QUnit.test('create analytic lines', async function (assert) {
        assert.expect(7);
        this.data['analytic.line'].fields.date.default = "2017-02-25";

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-02-25",
            viewOptions: {
                action: {
                    views: [{viewID: 23, type: 'form'}],
                },
            },
        });

        const mockRPC = (route, args) => {
            if (args.method === 'create') {
                assert.strictEqual(args.args[0].date, "2017-02-25",
                    "default date should be current day");
            }
        };
        await prepareWowlFormViewDialogs({ models: this.data, views: this.archs }, mockRPC);

        assert.containsNone(grid, '.o_grid_nocontent_container',
            "should not have rendered a no content helper");

        assert.containsNone(grid, 'div.o_grid_cell_container', "should not have any cells");
        assert.notOk($('.modal').length, "should not have any modal open");
        await testUtils.dom.click(grid.$buttons.find('.o_grid_button_add'));

        assert.ok($('.modal').length, "should have opened a modal");

        // input a project and a task
        const target = getFixture();
        await clickDropdown(target, "project_id");
        await clickOpenedDropdownItem(target, "project_id", "P1");
        await clickDropdown(target, "task_id");
        await clickOpenedDropdownItem(target, "task_id", "BS task");

        // input unit_amount
        await editInput(target, '.modal .o_field_widget[name=unit_amount] input', "4");

        // save
        await testUtils.dom.click($('.modal .modal-footer button.btn-primary'));

        assert.containsN(grid, 'div.o_grid_cell_container', 7,
            "should have 7 cell containers (1 for each day)");

        assert.strictEqual(grid.$('td.o_grid_total:contains(4:00)').length, 1,
            "should have a total of 4:00");

        grid.destroy();
    });

    QUnit.test('create analytic lines on grouped grid view', async function (assert) {
        assert.expect(4);
        this.data['analytic.line'].fields.date.default = "2017-02-25";

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"  section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-02-25",
            viewOptions: {
                action: {
                    views: [{viewID: 23, type: 'form'}],
                },
            },
            domain: [['date', '>', '2014-09-09']],
            mockRPC: function (route, args) {
                if (args.method === 'read_grid_grouped') {
                    assert.deepEqual(args.kwargs.domain, [['date', '>', '2014-09-09']],
                        "the action domain should always be given");
                }
                return this._super(route, args);
            },
        });

        const mockRPC = (route, args) => {
            if (args.method === 'create') {
                assert.strictEqual(args.args[0].date, "2017-02-25",
                    "default date should be current day");
            }
        };
        await prepareWowlFormViewDialogs({ models: this.data, views: this.archs }, mockRPC);

        await testUtils.dom.click(grid.$buttons.find('.o_grid_button_add'));
        assert.ok($('.modal').length, "should have opened a modal");
        // input a project and a task
        const target = getFixture();
        await clickDropdown(target, "project_id");
        await clickOpenedDropdownItem(target, "project_id", "P1");
        await clickDropdown(target, "task_id");
        await clickOpenedDropdownItem(target, "task_id", "BS task");
        // input unit_amount
        await editInput(target, '.modal .o_field_widget[name=unit_amount] input', "4");
        // save
        await testUtils.dom.click($('.modal .modal-footer button.btn-primary'));

        grid.destroy();
    });

    QUnit.test('switching active range', async function (assert) {
        assert.expect(6);
        this.data['analytic.line'].fields.date.default = "2017-02-25";

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-02-25",
        });

        assert.strictEqual(grid.$('thead th:not(.o_grid_title_header)').length, 8,
            "should have 8 columns (1 for each day + 1 for total)");
        assert.hasClass(grid.$buttons.find('button.grid_arrow_range[data-name="week"]'),'active',
            "current range is shown as active");
        assert.doesNotHaveClass(grid.$buttons.find('button.grid_arrow_range[data-name="month"]'), 'active',
            "month range is not active");

        await testUtils.dom.click(grid.$buttons.find('button[data-name=month]'));
        assert.strictEqual(grid.$('thead th:not(.o_grid_title_header)').length, 29,
            "should have 29 columns (1 for each day + 1 for total)");
        assert.hasClass(grid.$buttons.find('button.grid_arrow_range[data-name="month"]'),'active',
            "month range is shown as active");
        assert.doesNotHaveClass(grid.$buttons.find('button.grid_arrow_range[data-name="week"]'), 'active',
            "week range is not active");

        grid.destroy();
    });

    QUnit.test('clicking on the info icon on a cell triggers a do_action', async function (assert) {
        assert.expect(5);

        var domain;

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            mockRPC: function () {
                return this._super.apply(this, arguments).then(function (result) {
                    domain = result.grid[0][2].domain;
                    return result;
                });
            }
        });

        assert.containsN(grid, 'i.o_grid_cell_information', 14,
            "should have 14 icons to open cell info");

        testUtils.mock.intercept(grid, 'do_action', function (event) {
            var action = event.data.action;

            assert.deepEqual(action.domain, domain, "should trigger a do_action with correct values");
            assert.strictEqual(action.name, "P1 - BS task",
                "should have correct action name");
            assert.strictEqual(action.context.default_project_id, 31, "should pass project_id in context when click on info icon on cell");
            assert.strictEqual(action.context.default_task_id, 1 , "should pass task_id in context when click on info icon on cell");
        });
        await testUtils.dom.click(grid.$('i.o_grid_cell_information').eq(2));

        grid.destroy();
    });

    QUnit.test('editing a value [REQUIRE FOCUS]', async function (assert) {
        assert.expect(12);

        const currentDate = "2017-01-25";
        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: currentDate,
            viewOptions: {
                context: {some_value: 2},
            },
            mockRPC: function (route, args) {
                if (args.method === 'search') {
                    return Promise.resolve([1, 2, 3, 4, 5]);
                }
                if (args.method === 'adjust_grid') {
                    assert.strictEqual(args.model, 'analytic.line',
                        'should call with correct model in env');
                    assert.deepEqual(args.kwargs.context, {
                            some_value: 2,
                            default_date: currentDate,
                            grid_anchor: currentDate,
                        },
                        'should call with correct context');
                    assert.strictEqual(args.args[0].length, 0,
                        'should call method with no specific res ids');

                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (event) {
                    assert.strictEqual(event.data.env.model, 'analytic.line',
                        'should call with correct model in env');
                    assert.deepEqual(event.data.env.context, {
                            some_value: 2,
                            default_date: currentDate,
                            grid_anchor: currentDate,
                        },
                        'should call with correct context in env');
                    assert.deepEqual(event.data.env.resIDs, [1, 2, 3, 4, 5],
                        'should call with correct resIDs in env');
                },
            },
        });

        var $cell = grid.$('.o_grid_cell_container:eq(0)');
        var $div = $cell.find('div.o_grid_input')
        assert.doesNotHaveClass($div, 'o_has_error',
        "input should not show any error at start");

        await testUtils.dom.triggerEvent($div,'focus');
        var $input = $cell.find('input.o_grid_input')
        var selection = window.getSelection();
        assert.strictEqual($(selection.focusNode)[0], $cell[0],
            "the cell is focused");
        assert.strictEqual($(document.activeElement)[0], $input[0],
            "the text in the cell is selected");
        $input[0].value = "abc";

        await testUtils.dom.triggerEvent($input,'blur');
        $div = $cell.find('div.o_grid_input')

        assert.hasClass($div,'o_has_error',
            "input should be formatted to show that there was an error");

        await testUtils.dom.triggerEvent($div,'focus');
        $input = $cell.find('input.o_grid_input')
        $input[0].value = "8.5";

        await testUtils.dom.triggerEvent($input,'blur');
        $div = $cell.find('div.o_grid_input')

        assert.doesNotHaveClass($div, 'o_has_error',
            "input should not be formatted like there is an error");
        assert.strictEqual($div.text(), "8:30",
            "text should have been properly parsed/formatted");

        await testUtils.dom.click(grid.$buttons.find('button:contains("Action")'));

        grid.destroy();
    });

    QUnit.test('editing a value does not glitch [REQUIRE FOCUS]', async function (assert) {
        assert.expect(3);

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            viewOptions: {
                context: {some_value: 2},
            },
            mockRPC: function (route, args) {
                if (args.method === 'search') {
                    return Promise.resolve([1, 2, 3, 4, 5]);
                }
                if (args.method === 'adjust_grid') {
                    const proms = [];
                    proms.push(new Promise(resolve => setTimeout(resolve, 50)));
                    proms.push(this._super.apply(this, arguments));
                    return Promise.all(proms);
                }
                return this._super.apply(this, arguments);
            },
        });

        const $cell = grid.$('.o_grid_cell_container:eq(0)');
        let $div = $cell.find('div.o_grid_input');
        await testUtils.dom.triggerEvent($div, 'focus');
        const $input = $cell.find('input.o_grid_input');
        await testUtils.dom.triggerEvent($input, 'focus');
        document.execCommand('insertText', false, "8.5");
        await testUtils.dom.triggerEvent($input, 'blur');
        $div = $cell.find('div.o_grid_input');
        assert.doesNotHaveClass($div, 'o_has_error',
            "input should not be formatted like there is an error");
        assert.strictEqual($div.text(), "8:30",
            "text should not go back to previous value (0:00).");
        await new Promise(resolve => setTimeout(resolve, 100));
        $div = $cell.find('div.o_grid_input');
        assert.strictEqual($div.text(), "8:30",
            "text should have been properly parsed/formatted");

        grid.destroy();
    });

    QUnit.test('changing timestamp removes errors [REQUIRE FOCUS]', async function (assert) {
        assert.expect(2);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
        });

        var $cell = grid.$('.o_grid_cell_container:eq(0)');
        var $div = $cell.find('div.o_grid_input')

        await testUtils.dom.triggerEvent($div,'focus');
        var $input = $cell.find('input.o_grid_input')
        $input[0].value = "abc";

        await testUtils.dom.triggerEvent($input,'blur');
        assert.strictEqual(grid.$('.o_grid_input.o_has_error').length, 1,
        "input should have one error");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));
        assert.strictEqual(grid.$('.o_grid_input.o_has_error').length, 0,
        "input should not have error anymore");
        grid.destroy();
    });

    QUnit.test('basic grid view, hide range button', async function (assert) {
        assert.expect(3);
        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            action: {
                views: [{viewID: 23, type: 'form'}],
            },
            context: {'hide_second_button': true}
        });

        assert.containsN(grid.$buttons, 'button.grid_arrow_range', 2, "should have only one range button displayed");
        assert.containsOnce(grid.$buttons, "button[data-name='week']", "should have week button displayed");
        assert.containsOnce(grid.$buttons, "button[data-name='year']", "should have year button displayed");

        grid.destroy();
    });

    QUnit.test('basic grid view, hide column/row total', async function (assert) {
        assert.expect(3);

        this.data['analytic.line'].records.push({ id: 8, project_id: 142, task_id: 54, date: "2017-01-25", unit_amount: 4 });
        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `<grid string="Timesheet" hide_line_total="true" hide_column_total="true">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            currentDate: "2017-01-25",
        });

        assert.containsNone(grid, 'tfoot', "should have no footer");
        assert.containsN(grid, 'thead th', 8,
            "header should have 8 cells, 1 for description and 7 for week days, total cell should not be there");
        assert.doesNotHaveClass(grid.$('tbody'), '.o_grid_total', "body grid total should not be there");

        grid.destroy();
    });

    QUnit.test('basic grid view, displayed footer as a barchart', async function (assert) {
        assert.expect(3);

        this.data['analytic.line'].records.push({
            id: 8, project_id: 142, task_id: 54, date: "2017-01-25", unit_amount: 4,
        });

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `<grid string="Timesheet" barchart_total="1" adjustment="object" adjust_name="adjust_grid">
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            currentDate: "2017-01-25",
        });

        assert.containsN(grid, '.o_grid_total_bar', 7, "should have a 7 div in the footer");

        // max height value is 90%
        assert.strictEqual(grid.el.querySelectorAll('tfoot .o_grid_total_bar')[2].style.height, '90%',
            "third column should have 90% height for total bar");

        // null value have 0px height
        assert.strictEqual(window.getComputedStyle(grid.el.querySelector('tfoot .o_grid_cell_null > .o_grid_total_bar')).height, '0px',
            "null value column should have 0% height for total bar");

        grid.destroy();
    });

    QUnit.test('compute correct cell value of barchart total', async function (assert) {
        assert.expect(2);

        this.data['analytic.line'].records.push({
            id: 8, project_id: 142, task_id: 54, date: "2017-01-25", unit_amount: 4,
        });

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `<grid string="Timesheet" barchart_total="1" adjustment="object" adjust_name="adjust_grid">
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            currentDate: "2017-01-25",
        });

        let cell = grid.el.querySelector('tbody tr:nth-child(2) td:nth-child(2) .o_grid_cell_container');
        let div = cell.querySelector('div.o_grid_input');

        await testUtils.dom.triggerEvent(div, 'focus');
        let input = cell.querySelector('input.o_grid_input');
        await testUtils.fields.editInput(input, "5:45");

        await testUtils.dom.triggerEvent(input, 'blur');
        assert.strictEqual(grid.el.querySelector('tfoot .o_grid_total_bar').style.height, '45%',
            "height of first total bar should be correctly computed");

        cell = grid.el.querySelector('tbody tr:nth-child(2) td:nth-child(5) .o_grid_cell_container');
        div = cell.querySelector('div.o_grid_input');

        await testUtils.dom.triggerEvent(div, 'focus');
        input = cell.querySelector('input.o_grid_input');
        await testUtils.fields.editInput(input, "3:50");

        await testUtils.dom.triggerEvent(input, 'blur');
        assert.strictEqual(grid.el.querySelector('tfoot td:nth-child(5) .o_grid_total_bar').style.height, '30%',
            "height of fourth cell should be correctly computed");

        grid.destroy();
    });

    QUnit.test('row and column are highlighted when hovering a cell', async function (assert) {
        assert.expect(29);

        this.data['analytic.line'].fields.validated = {
            string: "Validation",
            type: "boolean"
        };
        this.data['analytic.line'].records.push({
            id: 8, project_id: 142, task_id: 54,
            date: "2017-01-25", unit_amount: 4,
            validated: true,
        });

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">
                    <field name="validated" type="readonly"/>
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>`,
            currentDate: "2017-01-25",
        });

        // check row highlighting
        assert.hasClass(grid.el.querySelector('table'), 'table-hover',
            "table has 'table-hover' class to highlight table rows on hover");

        // check column highlighting on th
        await testUtils.dom.triggerEvents(grid.el.querySelectorAll('thead th')[2], 'mouseover');
        assert.containsN(grid, 'tbody .o_cell_hover', 5);
        for (let i = 0; i < 5; i++) {
            assert.hasClass(grid.$(`tbody tr:nth(${i}) td:nth(1)`), 'o_cell_hover');
        }
        await testUtils.dom.triggerEvents(grid.el.querySelectorAll('thead th')[2], 'mouseout');
        assert.containsNone(grid, '.o_cell_hover');

        // check column highlighting on th of o_grid_total cell
        await testUtils.dom.triggerEvents(grid.el.querySelectorAll('thead th')[8], 'mouseover');
        assert.containsN(grid, 'tbody .o_cell_hover', 5);
        for (let i = 0; i < 5; i++) {
            assert.hasClass(grid.$(`tbody tr:nth(${i}) td:nth(7)`), 'o_cell_hover');
        }
        await testUtils.dom.triggerEvents(grid.el.querySelectorAll('thead th')[8], 'mouseout');
        assert.containsNone(grid, '.o_cell_hover');

        // hover second cell, second row
        const cell = grid.el.querySelector('tbody tr:nth-child(2) td:nth-child(3)');
        await testUtils.dom.triggerEvents(cell, 'mouseover');
        assert.containsN(grid, '.o_cell_hover', 7);
        // leading zero in hour are not displayed on hover, in input mode leading zero displayed
        assert.strictEqual(cell.innerText, '0:00',
            "in non edit mode there not be leading zero in hours");

        const div = cell.querySelector('div.o_grid_input');
        await testUtils.dom.triggerEvent(div, 'focus');
        assert.strictEqual(cell.querySelector('input.o_grid_input').value, '0:00',
            "in non edit mode there not be leading zero in hours");

        await testUtils.dom.triggerEvents(cell, 'mouseout');
        assert.containsNone(grid, '.o_cell_hover');

        // check column highlighted on hover section row cell, hover on first row, first cell
        await testUtils.dom.triggerEvents(grid.el.querySelector('tbody tr:nth-child(1) td:nth-child(2)'), 'mouseover');
        assert.containsN(grid, '.o_cell_hover', 7);
        await testUtils.dom.triggerEvents(grid.el.querySelector('tbody tr:nth-child(1) td:nth-child(2)'), 'mouseout');
        assert.containsNone(grid, '.o_cell_hover');

        // check column highlighted on mouse hover on footer cell
        await testUtils.dom.triggerEvents(grid.el.querySelector('tfoot tr td:nth-child(2)'), 'mouseover');
        assert.containsN(grid, '.o_cell_hover', 7);
        await testUtils.dom.triggerEvents(grid.el.querySelector('tfoot tr td:nth-child(2)'), 'mouseout');
        assert.containsNone(grid, '.o_cell_hover');

        // check column highlighted on mouse hover on o_grid_total cell
        await testUtils.dom.triggerEvents(grid.el.querySelector('tbody tr:nth-child(1) td.o_grid_total'), 'mouseover');
        assert.containsN(grid, '.o_cell_hover', 7);
        await testUtils.dom.triggerEvents(grid.el.querySelector('tbody tr:nth-child(1) td.o_grid_total'), 'mouseout');
        assert.containsNone(grid, '.o_cell_hover');

        // check column highlighted on mouse hover on o_grid_super cell
        await testUtils.dom.triggerEvents(grid.el.querySelector('tfoot tr td:nth-child(9)'), 'mouseover');
        assert.containsN(grid, '.o_cell_hover', 7);
        await testUtils.dom.triggerEvents(grid.el.querySelector('tfoot tr td:nth-child(9)'), 'mouseout');
        assert.containsNone(grid, '.o_cell_hover');

        // null section value have opacity 0.2
        assert.strictEqual(window.getComputedStyle(grid.el.querySelector('.o_grid_cell_null > div')).opacity, '0.2');

        // no leading zero in readonly cell
        assert.strictEqual(grid.el.querySelector('tbody .o_grid_cell_readonly').innerText, '4:00');

        grid.destroy();
    });

    QUnit.test('grid view with type="readonly" field', async function (assert) {
        assert.expect(4);
        var done = assert.async();
        this.data['analytic.line'].fields.validated = {string: "Validation", type: "boolean"};
        this.data['analytic.line'].records.push({id: 8, project_id: 142, task_id: 54, date: "2017-01-25", unit_amount: 4, validated: true});
        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="validated" type="readonly"/>' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-01-25",
        });
        return concurrency.delay(0).then(function () {
            assert.strictEqual(grid.$('.o_grid_cell_container:not(.o_grid_cell_empty)').length, 3,
                "should have 3 columns which has timesheet value");
            assert.strictEqual(grid.$('.o_grid_cell_container:not(.o_grid_cell_readonly, .o_grid_cell_empty)').length, 2,
                "should have 2 cells which are not readonly");
            assert.strictEqual(grid.$('.o_grid_cell_readonly').length, 1,
                "should have 1 cell which is readonly");
            assert.doesNotHaveClass(grid.$('.o_grid_cell_readonly div'), 'o_grid_input',
                "should not have o_grid_input class on readonly cell");
            grid.destroy();
            done();
        });
    });

    QUnit.test('grid_anchor is properly transferred in context', async function (assert) {
        assert.expect(1);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day" invisible="context.get(\'hide_second_button\')"/>' +
                        '<range name="year" string="Year" span="year" step="month"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-01-31",
            mockRPC: function (route, args) {
                if (args.method === 'adjust_grid') {
                    assert.strictEqual(args.kwargs.context.grid_anchor, '2017-01-24',
                        "proper grid_anchor is sent to server");
                }
                return this._super.apply(this, arguments);
            },
        });

        // go back to previous week, to be able to check if grid_anchor is
        // properly updated and sent to the server
        await testUtils.dom.click(grid.$buttons.find('.grid_arrow_previous'));

        var $cell = grid.$('.o_grid_cell_container:eq(0)');
        var $div = $cell.find('div.o_grid_input')
        await testUtils.dom.triggerEvent($div,'focus');
        var $input = $cell.find('input.o_grid_input')
        $input[0].value = "2";
        await testUtils.dom.triggerEvent($input,'blur');

        await testUtils.nextTick();

        grid.destroy();
    });

    QUnit.test('grid_anchor stays when navigating', async function (assert) {
        assert.expect(3);
        const views = {
            'analytic.line,false,grid': '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                '<field name="project_id" type="row"/>' +
                '<field name="task_id" type="row"/>' +
                '<field name="date" type="col">' +
                    '<range name="week" string="Week" span="week" step="day"/>' +
                    '<range name="month" string="Month" span="month" step="day"/>' +
                    '<range name="year" string="Year" span="year" step="month"/>' +
                '</field>'+
                '<field name="unit_amount" type="measure" widget="float_time"/>' +
            '</grid>',
            'analytic.line,false,search': '<search>' +
                    '<filter name="filter_test" help="Project 31" domain="[(\'project_id\', \'=\', 31)]"/>' +
            '</search>',
        };
        const serverData = {models: this.data, views};

        const target = getFixture();

        // create an action manager to test the interactions with the search view
        const webClient = await createWebClient({
            serverData,
            legacyParams: { withLegacyMockServer: true },
        });

        await doAction(webClient, {
            res_model: 'analytic.line',
            type: 'ir.actions.act_window',
            views: [[false, 'grid']],
            context: {
                'search_default_filter_test': 1,
                'grid_anchor': '2017-01-31',
            },
        });

        // check first column header
        assert.strictEqual($(target).find('.o_view_grid th:eq(2)').text(), "Tue,Jan 31", "The first day of the span should be the 31st of January");

        // move to previous week, and check first column header
        await testUtils.dom.click($(target).find('.o_control_panel .grid_arrow_previous'));
        assert.strictEqual($(target).find('.o_view_grid th:eq(2)').text(), "Tue,Jan 24", "The first day of the span should be the 24st of January, as we check the previous week");

        // remove the filter in the searchview
        await testUtils.dom.click($(target).find('.o_control_panel .o_searchview .o_facet_remove'));

        // recheck first column header
        assert.strictEqual($(target).find('.o_view_grid th:eq(2)').text(), "Tue,Jan 24", "The first day of the span should STILL be the 24st of January, even we resetting search");
    });

    QUnit.test('grid with two tasks with same name, and widget', async function (assert) {
        assert.expect(2);

        this.data.task.records = [
            { id: 1, display_name: "Awesome task", project_id: 31 },
            { id: 2, display_name: "Awesome task", project_id: 31 }
        ];
        this.data['analytic.line'].records = [
            { id: 1, task_id: 1, date: "2017-01-30", unit_amount: 2 },
            { id: 2, task_id: 2, date: "2017-01-31", unit_amount: 5.5 },
        ];
        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `
                <grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_toggle"/>'
                </grid>`,
            currentDate: "2017-01-31",
        });

        assert.containsN(grid, '.o_view_grid tbody tr:not(.o_grid_padding)', 2);
        assert.strictEqual(grid.$('.o_view_grid tbody tr th').text().trim(), "Awesome taskAwesome task");

        grid.destroy();
    });

    QUnit.test('"create_inline is truthy', async function (assert) {
        assert.expect(3);

        this.arch = '<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid" create_inline="1">' +
                        '<field name="project_id" type="row" section="1"/>' +
                        '<field name="task_id" type="row"/>' +
                        '<field name="date" type="col">' +
                            '<range name="week" string="Week" span="week" step="day"/>' +
                            '<range name="month" string="Month" span="month" step="day"/>' +
                        '</field>' +
                        '<field name="unit_amount" type="measure" widget="float_time"/>' +
                    '</grid>';

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            viewOptions: {
                action: {
                    views: [{viewID: 23, type: 'form'}],
                },
            },
        });
        await prepareWowlFormViewDialogs({ models: this.data, views: this.archs });
        assert.ok(grid.$buttons.find('.o_grid_button_add').is(':hidden'), "'Add a line' control panel button should not be visible");
        const $addLineRow = grid.$('tr.o_grid_add_line_row th div div a[role="button"]:contains("Add a line")');
        assert.strictEqual($addLineRow.length, 1, "'Add a line' row should be visible");
        await testUtils.dom.click($addLineRow);
        assert.ok($('.modal').length, "should have opened a modal");
        await testUtils.dom.click($('.modal .modal-footer button.o_form_button_cancel'));
        grid.destroy();
    });

    QUnit.test('"create_inline is truthy with no data', async function (assert) {
        assert.expect(2);

        this.arch = '<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid" create_inline="1">' +
                        '<field name="project_id" type="row" section="1"/>' +
                        '<field name="task_id" type="row"/>' +
                        '<field name="date" type="col">' +
                            '<range name="week" string="Week" span="week" step="day"/>' +
                            '<range name="month" string="Month" span="month" step="day"/>' +
                        '</field>' +
                        '<field name="unit_amount" type="measure" widget="float_time"/>' +
                    '</grid>';

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2000-01-01",
            viewOptions: {
                action: {
                    views: [{viewID: 23, type: 'form'}],
                },
            },
        });
        await prepareWowlFormViewDialogs({ models: this.data, views: this.archs });
        const $addLineButton = grid.$buttons.find('.o_grid_button_add');
        assert.ok($addLineButton.is(':visible'), "'Add a line' control panel button should be visible");
        await testUtils.dom.click($addLineButton);
        assert.ok($('.modal').length, "should have opened a modal");
        await testUtils.dom.click($('.modal .modal-footer button.o_form_button_cancel'));
        grid.destroy();
    });

    QUnit.test('"create_inline is truthy but create is falsy', async function (assert) {
        assert.expect(2);

        this.arch = '<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid" create_inline="1" create="0">' +
                        '<field name="project_id" type="row" section="1"/>' +
                        '<field name="task_id" type="row"/>' +
                        '<field name="date" type="col">' +
                            '<range name="week" string="Week" span="week" step="day"/>' +
                            '<range name="month" string="Month" span="month" step="day"/>' +
                        '</field>' +
                        '<field name="unit_amount" type="measure" widget="float_time"/>' +
                    '</grid>';

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
        });
        assert.strictEqual(grid.$buttons.find('.o_grid_button_add').length, 0, "'Add a line' control panel button should not be rendered");
        assert.strictEqual(grid.$('tr.o_grid_add_line_row th div div a[role="button"]:contains("Add a line")').length, 0, "'Add a line' row should not be visible");
        grid.destroy();
    });

    QUnit.test('"create_inline is truthy with no data and display_empty is truthy', async function (assert) {
        assert.expect(3);

        this.arch = '<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid" create_inline="1" display_empty="1">' +
                        '<field name="project_id" type="row" section="1"/>' +
                        '<field name="task_id" type="row"/>' +
                        '<field name="date" type="col">' +
                            '<range name="week" string="Week" span="week" step="day"/>' +
                            '<range name="month" string="Month" span="month" step="day"/>' +
                        '</field>' +
                        '<field name="unit_amount" type="measure" widget="float_time"/>' +
                    '</grid>';

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2000-01-01",
            viewOptions: {
                action: {
                    views: [{viewID: 23, type: 'form'}],
                },
            },
        });
        await prepareWowlFormViewDialogs({ models: this.data, views: this.archs });
        assert.ok(grid.$buttons.find('.o_grid_button_add').is(':hidden'), "'Add a line' control panel button should not be visible");
        const $addLineRow = grid.$('tr.o_grid_add_line_row th div div a[role="button"]:contains("Add a line")');
        assert.strictEqual($addLineRow.length, 1, "'Add a line' row should be visible");
        await testUtils.dom.click($addLineRow);
        assert.ok($('.modal').length, "should have opened a modal");
        await testUtils.dom.click($('.modal .modal-footer button.o_form_button_cancel'));
        grid.destroy();
    });

    QUnit.module('GridViewComponents');

    QUnit.test('float_toggle component', async function (assert) {
        assert.expect(25);
        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_toggle" options="{\'factor\': 0.125, \'range\': [0.0, 0.5, 1.0]}"/>' +
                '</grid>',
            currentDate: "2017-01-31",
            async mockRPC(route, args) {
                if (args.method === 'adjust_grid') {
                    if (args.args[3] == '2017-02-01/2017-02-02') { // use case "clicking on empty cell button"
                        assert.strictEqual(args.args[5], 4, "saving 0.5 on float_toggle button will register 4 in database (0.5 / 0.125)");
                    }
                    if (args.args[3] == '2017-01-30/2017-01-31') { // use case "clicking on non empty cell button"
                        assert.strictEqual(args.args[5], -10, "saving 0.00 on float_toggle button will send a negative delta of 1.25 / 0.125");
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        // Bypass debounce on cell clicks
        patchWithCleanup(browser, {
            setTimeout(cb) {
                return setTimeout(cb, 0);
            }
        });

        // first section
        assert.strictEqual(grid.$('.o_grid_section:eq(0) button.o_grid_float_toggle').length, 7,
            "first section should be for project P1");
        assert.strictEqual(grid.$('.o_grid_section:eq(0) button.o_grid_float_toggle:contains(1.25)').length, 1,
            "one button contains the value 1.25 (timesheet line #4)");
        assert.strictEqual(grid.$('.o_grid_section:eq(0) button.o_grid_float_toggle:contains(0.00)').length, 6,
            "Other button are filled with 0.00");
        assert.strictEqual(grid.$('.o_grid_section:eq(0) .o_grid_cell_container:eq(0) button').text(), '1.25',
            "the second cell of the second section is the timesheet #4");

        // second section
        assert.strictEqual(grid.$('.o_grid_section:eq(1) button.o_grid_float_toggle').length, 7,
            "first section should be for project Webocalypse Now");
        assert.strictEqual(grid.$('.o_grid_section:eq(1) button.o_grid_float_toggle:contains(-0.44)').length, 1,
            "one button contains the value -0.44 (timesheet line #5)");
        assert.strictEqual(grid.$('.o_grid_section:eq(1) button.o_grid_float_toggle:contains(0.00)').length, 6,
            "Other button are filled with 0.00");
        assert.strictEqual(grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(1) button').text(), '-0.44',
            "the second cell of the second section is the timesheet #5");
        assert.hasClass(grid.$('.o_grid_section:eq(1) tr:eq(0) td:eq(1)'), 'text-danger',
            "the second cell of the second section has text-danger class as it has negative value");
        assert.hasClass(grid.$('.o_grid_section:eq(1) tr:eq(1) td:eq(1) button.o_grid_float_toggle'), 'text-danger',
            "the second cell with float_togggle widget of the second section has text-danger class as it has negative value");

        // clicking on empty cell button
        assert.strictEqual(grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button').text(), '0.00',
        "0.00 before we click on it");
        var $button = grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button');
        $button.focus();

        await testUtils.dom.click($button);
        assert.strictEqual(grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button').text(), '0.50',
            "0.5 is the next value since 0.0 was the closest value in the range");

        await testUtils.nextTick();

        await testUtils.dom.click($button);
        assert.strictEqual(grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button').text(), '1.00',
            "0.5 becomes 1.0 as it is the next value in the range");

        await testUtils.nextTick();

        // clicking on non empty cell button (1.25)
        var $button = grid.$('.o_grid_section:eq(0) .o_grid_cell_container:eq(0) button');

        await testUtils.dom.click($button);
        assert.strictEqual(grid.$('.o_grid_section:eq(0) .o_grid_cell_container:eq(0) button').text(), '0.00',
            "1.25 is starting value, the closest in the range is 1.00, so the next will be 0.00");

        assert.strictEqual(grid.$('tfoot tr td:eq(6) div').text(), '0.00',
            "The sixth cell of the footer should contain 0.00");
        assert.strictEqual(grid.$('tbody tr:eq(1) td.o_grid_total').text(), '0.00',
            "The total of the BS task should be 0.00");
        var $button = grid.$('.o_grid_section:eq(0) .o_grid_cell_container:eq(5) button');
        $button.focus();
        await testUtils.dom.click($button);
        $button.blur();
        assert.strictEqual(grid.$('tfoot tr td:eq(6) div').text(), '0.50',
            "The fourth cell of the footer should contain 0.50");
        assert.strictEqual(grid.$('tbody tr:eq(1) td.o_grid_total').text(), '0.50',
            "The total of the BS task should be 0.50");

        assert.strictEqual(grid.$('tfoot tr td:eq(4) div').text(), '0.00',
            "The fifth cell of the footer should contain 0.00");
        assert.strictEqual(grid.$('tbody tr:eq(1) td.o_grid_total').text(), '0.50',
            "The total of the BS task should be 0.50");
        var $button = grid.$('.o_grid_section:eq(0) .o_grid_cell_container:eq(4) button');
        $button.focus();
        await testUtils.dom.click($button);
        $button.blur();
        assert.strictEqual(grid.$('tfoot tr td:eq(5) div').text(), '0.50',
            "The fifth cell of the footer should contain 0.50");
        assert.strictEqual(grid.$('tbody tr:eq(1) td.o_grid_total').text(), '1.00',
            "The total of the BS task should be 0.00");
        await testUtils.nextTick();
        grid.destroy();
    });

    QUnit.test('float_toggle component comma', async function (assert) {
        assert.expect(3);
        let grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_toggle" options="{\'factor\': 0.125, \'range\': [0.0, 0.5, 1.0]}"/>' +
                '</grid>',
            currentDate: "2017-01-31",
            translateParameters: {
                thousands_sep: ".",
                decimal_point: ",",
            },
        });

        // Bypass debounce on cell clicks
        patchWithCleanup(browser, {
            setTimeout(cb) {
                return setTimeout(cb, 0);
            }
        });

        // clicking on empty cell button
        assert.strictEqual(grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button').text(), '0,00',
        "0,00 before we click on it");
        let $button = grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button');
        $button.focus();

        await testUtils.dom.click($button);
        assert.strictEqual(grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button').text(), '0,50',
            "0,5 is the next value since 0,0 was the closest value in the range");
        await testUtils.nextTick();
        await testUtils.dom.click($button);
        assert.strictEqual(grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button').text(), '1,00',
            "0,5 becomes 1,0 as it is the next value in the range");

        await testUtils.nextTick();
        grid.destroy();
    });

    QUnit.test('button context not polluted by previous click', async function (assert) {
        assert.expect(4);

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-31",
            mockRPC: function (route, args) {
                if (route === 'some-image') {
                    return Promise.resolve();
                }
                if (args.method === 'search') {
                    return Promise.resolve([1, 2, 3, 4, 5]);
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (event) {
                    if (event.data.action_data.name === 'action_name') {
                        assert.step(event.data.action_data.context.grid_anchor);
                    }
                },
            },
        });
        testUtils.dom.click(grid.$buttons.find('.grid_arrow_previous'));

        // check that first button click does not affect that button
        // context for subsequent clicks on it
        await testUtils.dom.click(grid.$buttons.find('button:contains("Action")'));
        assert.verifySteps(['2017-01-24'],
            'first button click get current grid anchor date');
        testUtils.dom.click(grid.$buttons.find('.grid_arrow_previous'));
        await testUtils.dom.click(grid.$buttons.find('button:contains("Action")'));
        assert.verifySteps(['2017-01-17'],
            'second button click get current grid anchor date');

        grid.destroy();
    });

    QUnit.test('grid view in day range ', async function (assert) {
        assert.expect(14);
        var nbReadGrid = 0;
        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `
                <grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">
                    <field name="project_id" type="row"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>
            `,
            currentDate: "2017-01-30",
            mockRPC: function (route, args) {
                if (args.method === 'read_grid') {
                    nbReadGrid++;
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.ok(grid.$('table').length, "Table rendered properly.");
        assert.strictEqual(nbReadGrid, 1, "should have read one grid by group")
        assert.containsOnce(grid, 'thead th:not(.o_grid_title_header)', "Single Day column should be shown");
        var grid_anchor = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(grid_anchor, "Mon,Jan30", "grid should start with grid_anchor date as the default date.");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));

        grid_anchor = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(grid_anchor, 'Tue,Jan31', "Date should be of next day.");
        assert.strictEqual(nbReadGrid, 2, "should have read one grid by group")
        assert.containsOnce(grid, 'thead th:not(.o_grid_title_header)', "Single Day column should be shown");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_previous'));

        grid_anchor = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(grid_anchor, "Mon,Jan30", "Date should be today's date.");
        assert.strictEqual(nbReadGrid, 3, "should have read one grid by group")
        assert.containsOnce(grid, 'thead th:not(.o_grid_title_header)', "Single Day column should be shown");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_previous'));

        grid_anchor = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(grid_anchor, 'Sun,Jan29', "Date should be of 29th Jan.");
        assert.strictEqual(nbReadGrid, 4, "should have read four read grid");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));

        grid_anchor = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(grid_anchor, 'Mon,Jan30', "Date should be of 30th Jan.");
        assert.strictEqual(nbReadGrid, 5, "should have five read grid");
        grid.destroy();
    });

    QUnit.test('basic grouped grid view in day range', async function (assert) {
        assert.expect(16);
        var nbReadGroup = 0;

        this.arch = `
            <grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid">
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="day" string="Day" span="day" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>
        `;

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            mockRPC: function (route, args) {
                if (args.method === 'read_grid_grouped') {
                    assert.strictEqual(args.kwargs.section_field, 'project_id',
                        "should have project_id as section_field on which view will be grouped");
                    nbReadGroup++;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(grid.$('table').length, "should have rendered a table");
        assert.strictEqual(nbReadGroup, 1, "should have one read_grid by group")
        assert.containsOnce(grid, 'thead th:not(.o_grid_title_header)', "Single Day column should be shown");
        assert.containsN(grid, '.o_grid_section', 2, "should have one section by project");

        // first section
        assert.containsOnce(grid, '.o_grid_section:eq(0) th:contains(P1)',
            "first section should be for project P1");
        assert.containsN(grid, '.o_grid_section:eq(0) div.o_grid_cell_container', 1,
            "first section should have 1 cells");
        assert.containsNone(grid, '.o_grid_section:eq(0) th:contains(None)',
            "first section should'nt have a row without task");
        assert.containsOnce(grid, '.o_grid_section:eq(0) th:contains(BS task)',
            "first section should have a row for BS task");

        var grid_anchor = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(grid_anchor, "Wed,Jan25", "grid should start with grid_anchor date as the default date.");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_next'));

        var next_date = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(next_date, 'Thu,Jan26', "Date should be of next day.");
        assert.containsOnce(grid, 'thead th:not(.o_grid_title_header)', "Single Day column should be shown");

        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_previous'));

        var previous_date = grid.$('thead tr').text().split(',\n').join().replace(/\s/g, '');
        assert.equal(previous_date, "Wed,Jan25", "Date should be today's date.");
        assert.containsOnce(grid, 'thead th:not(.o_grid_title_header)', "Single Day column should be shown");
        grid.destroy();
    });

    QUnit.test('work well with selection fields', async function (assert) {
        assert.expect(1);

        this.data['analytic.line'].fields.foo = {
            type: "selection",
            selection: [['a', 'A'], ['b', 'B']]
        };
        this.data['analytic.line'].records.forEach(function (record) {
            record.foo = "a";
        });

        this.arch = '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
            '<field name="project_id" type="row"/>' +
            '<field name="foo" type="row"/>' +
            '<field name="date" type="col">' +
                '<range name="week" string="Week" span="week" step="day"/>' +
                '<range name="month" string="Month" span="month" step="day" invisible="context.get(\'hide_second_button\')"/>' +
                '<range name="year" string="Year" span="year" step="month"/>' +
            '</field>'+
            '<field name="unit_amount" type="measure" widget="float_time"/>' +
        '</grid>';


        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-25",
            mockRPC: function (route) {
                if (route === 'some-image') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(grid.$('th div').first()[0].textContent, `P1A`,
            "should render properly selection value");
        grid.destroy();
    });

    QUnit.test('button disabled after click', async function (assert) {
        /*
         * OPW 2121906
         * We disable the button and enable it only when the RPC call is done.
         * Without this limitation, stressing the view can cause concurrency issues.
         */

        assert.expect(3);
        const def = testUtils.makeTestPromise();
        let rpcCalled = false;
        const params =  {
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_toggle" options="{\'factor\': 0.125, \'range\': [0.0, 0.5, 1.0]}"/>' +
                '</grid>',
            currentDate: "2017-01-31",
            async mockRPC (route, args) {
                if (args.method === 'adjust_grid') {
                    rpcCalled = true;
                    await def;
                }
                return this._super.apply(this, arguments);
            },
        }
        const grid = await createView(params);
        const $button = grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(0) button');
        $button.focus();
        testUtils.dom.click($button);

        await testUtils.nextTick();

        assert.ok(rpcCalled, 'The RPC should be called');
        assert.ok($button.is(':disabled'), 'The button is disabled while the RPC call is not done');

        def.resolve();
        await testUtils.nextTick();

        assert.notOk($button.is(':disabled'), 'The button is enabled when the RPC call is done');
        grid.destroy();
    });

    QUnit.test('each button\'s value is correct after RPC call', async function (assert) {
        /*
         * OPW 2121906
         * We disable the button and enable it only when the RPC call is done.
         * Without this limitation, stressing the view can cause concurrency issues.
         */
        assert.expect(3);
        const def = testUtils.makeTestPromise();
        let rpcCalled = false;

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_toggle" options="{\'factor\': 0.125, \'range\': [0.0, 0.5, 1.0]}"/>' +
                '</grid>',
            currentDate: "2017-01-31",
            async mockRPC (route, args) {
                if (args.method === 'adjust_grid') {
                    rpcCalled = true;
                    await def;
                }
                return this._super.apply(this, arguments);
            },
        });

        var $button1 = grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(0) button');
        var $button2 = grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(2) button');

        $button1.focus();
        $button1.click();
        await testUtils.nextTick();
        assert.ok(rpcCalled, 'The RPC should be called');

        $button2.click();
        def.resolve();
        await testUtils.nextTick();

        assert.strictEqual($button1.text(), '0.50');
        assert.strictEqual($button2.text(), '0.50');
        grid.destroy();
    });

    QUnit.test('create/edit disabled for readonly grid view', async function (assert) {
        assert.expect(4);
        this.data['analytic.line'].fields.validated = {string: "Validation", type: "boolean"};
        this.data['analytic.line'].records.push({id: 8, project_id: 142, task_id: 54, date: "2017-01-25", unit_amount: 4, validated: true});

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet" adjustment="object" adjust_name="adjust_grid" create="false" edit="false">' +
                    '<field name="validated" type="readonly"/>' +
                    '<field name="project_id" type="row"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                        '<range name="month" string="Month" span="month" step="day"/>' +
                    '</field>' +
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            currentDate: "2017-01-25",
        });
        assert.containsNone(grid, '.o_grid_cell_container:eq(3):not(.o_grid_cell_empty) .fa-search-plus',
            "should not have magnifying glass icon");
        assert.containsOnce(grid, '.o_grid_cell_container:eq(2):not(.o_grid_cell_empty) .fa-search-plus',
            "should have magnifying glass icon to move on tree view");
        testUtils.mock.intercept(grid, 'do_action', function (event) {
            const action = event.data.action;
            assert.strictEqual(action.context.create, false, "It should not be createable");
            assert.strictEqual(action.context.edit, false, "It should not be editable");
        });
        await testUtils.dom.click(grid.$('div.o_grid_cell_container:eq(2) .o_grid_cell_information'));

        grid.destroy();
    });

    QUnit.test("concurrent reloads of a grid view (from 2 to 1 to 2 groupbys quickly)", async function (assert) {
        assert.expect(12);

        const prom = testUtils.makeTestPromise();

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `
                <grid string="Timesheet" adjustment="object" adjust_name="adjust_grid">
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="day" string="Day" span="day" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_time"/>
                </grid>
            `,
            archs: {
                'analytic.line,false,search': `
                    <search>
                        <filter name="Project" context="{'group_by': 'project_id'}"/>
                    </search>
                `,
            },
            currentDate: "2017-01-30",
            mockRPC: async function (_, args) {
                const _super = this._super.bind(this);
                if (args.method === 'read_grid_grouped' && !args.kwargs.row_fields.length) {
                    await prom;
                    // _mockReadGrid does not work when row_fields has zero length.
                    // Here we will use the results from a call to read_grid
                    // with row_fields = ['task_id'] (initial case) but we
                    // set the row values as {} like they should be
                    // Most domains won't be good in result but we don't care.
                    // The form of result will be good apart from that
                    args.kwargs.row_fields = ['task_id'];
                    const result = await _super(...arguments);
                    for (const r of result.rows) {
                        r.values = {};
                    }
                    return result;
                }
                return _super(...arguments);
            },
        });

        assert.containsOnce(grid, ".o_grid_section tr div[title='BS task']");
        assert.deepEqual(grid.model.groupedBy, ['project_id', 'task_id'], "two groupbys");
        assert.deepEqual(grid.model._gridData.groupBy, ['project_id', 'task_id'], "two groupbys");

        // open Group By menu
        await cpHelpers.toggleGroupByMenu(grid.el);
        // click on Project
        await cpHelpers.toggleMenuItem(grid.el, 'Project');

        // the data has not been fetched yet (the calls to read_grid take time)
        assert.containsOnce(grid, ".o_grid_section tr div[title='BS task']");
        assert.deepEqual(grid.model.groupedBy, ['project_id'], "one groupby");
        assert.deepEqual(grid.model._gridData.groupBy, ['project_id', 'task_id'], "_gridData has not been modified yet");

        // click again on Project while the data are being fetched (the read_grid results have not returned yet)
        await cpHelpers.toggleMenuItem(grid.el, 'Project');

        assert.containsOnce(grid, ".o_grid_section tr div[title='BS task']");
        assert.deepEqual(grid.model.groupedBy, ['project_id', 'task_id'], "two groupbys");
        assert.deepEqual(grid.model._gridData.groupBy, ['project_id', 'task_id'], "two groupbys");

        prom.resolve();
        await testUtils.nextTick();

        assert.containsOnce(grid, ".o_grid_section tr div[title='BS task']");
        assert.deepEqual(grid.model.groupedBy, ['project_id', 'task_id'], "the model state has not been corrupted");
        assert.deepEqual(grid.model._gridData.groupBy, ['project_id', 'task_id'], " the model state has not been corrupted");

        grid.destroy();
    });

    QUnit.test('Unavailable day is greyed', async function (assert) {
        assert.expect(1);

        this.data['analytic.line'].records.push(
            {id: 6, project_id: 142, task_id: 12, date: "2020-06-23", unit_amount: 3.5}
        );

        this.arch = '<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid">' +
                '<field name="project_id" type="row" section="1"/>' +
                '<field name="task_id" type="row"/>' +
                '<field name="date" type="col">' +
                    '<range name="week" string="Week" span="week" step="day"/>' +
                    '<range name="month" string="Month" span="month" step="day"/>' +
                '</field>'+
                '<field name="unit_amount" type="measure" widget="float_time"/>' +
            '</grid>';

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2020-06-22",
        });
        assert.containsN(grid, '.o_grid_unavailable', 7, "should have 7 unavailable elements");
        grid.destroy();
    });

    QUnit.test('adjustment of type action should execute given action', async function (assert) {
        assert.expect(9);

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `
                <grid string="Timesheet" adjustment="action" adjust_name="123">
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_toggle" options="{'factor': 0.125, 'range': [0.0, 0.5, 1.0]}"/>
                </grid>`,
            currentDate: "2017-01-31",
            intercepts: {
                execute_action: function (event) {
                    const data = event.data;
                    const context = data.action_data.context;
                    assert.strictEqual(data.env.model, 'analytic.line', "should have correct model");
                    assert.strictEqual(data.action_data.name, '123', "should call correct action id");
                    assert.ok(context.grid_adjust.row_domain, 'row_domain should be in action context');
                    assert.ok(context.grid_adjust.column_field, 'column_field should be in action context');
                    assert.ok(context.grid_adjust.column_value, 'column_value should be in action context');
                    assert.ok(context.grid_adjust.cell_field, 'cell_field should be in action context');
                    assert.ok(context.grid_adjust.change, 'change should be in action context');
                }
            },
        });

        const $button = grid.$('.o_grid_section:eq(1) .o_grid_cell_container:eq(0) button');
        assert.strictEqual($button.text(), '0.00');

        $button.focus();
        $button.click();
        await testUtils.nextTick();

        assert.strictEqual($button.text(), '0.50');
        grid.destroy();
    });

    QUnit.test('display the grid if the first row is empty', async function (assert) {
        assert.expect(1);
        this.arch = `<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid">
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`;

        this.data['analytic.line'].records = [];
        this.data['analytic.line'].records.push({id: 2, project_id: 31, task_id: 1, date: "2017-01-10", unit_amount: 0});
        this.data['analytic.line'].records.push({id: 6, project_id: 142, task_id: 12, date: "2017-01-26", unit_amount: 3.5});

        var grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2017-01-24",
            viewOptions: {
                noContentHelp: `<p class="o_view_nocontent_smiling_face">
                        No activities found. Let's start a new one!
                    </p>`
            }
        });

        assert.containsOnce(grid, '.o_view_grid', "Grid should be shown");

        grid.destroy();
    });

    QUnit.test('update context to get the current date when the current date is in the range.', async function (assert) {
        assert.expect(8);

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: `
                <grid string="Timesheet" adjustment="action" adjust_name="123">
                    <field name="project_id" type="row" section="1"/>
                    <field name="task_id" type="row"/>
                    <field name="date" type="col">
                        <range name="week" string="Week" span="week" step="day"/>
                        <range name="month" string="Month" span="month" step="day"/>
                    </field>
                    <field name="unit_amount" type="measure" widget="float_toggle" options="{'factor': 0.125, 'range': [0.0, 0.5, 1.0]}"/>
                </grid>`,
            currentDate: "2017-01-31",
            context: {grid_range: 'week'},
        });

        const $weekRangeButton = grid.$buttons.find('button.grid_arrow_range[data-name="week"]');
        const $monthRangeButton = grid.$buttons.find('button.grid_arrow_range[data-name="month"]');
        assert.hasClass($weekRangeButton,'active', 'current range is shown as active');
        assert.strictEqual(grid.model.getContext().grid_anchor, '2017-01-31', 'the grid anchor should be the current date.');
        assert.strictEqual(grid.model.getContext().grid_range, 'week', 'the grid range should be "week".');
        await testUtils.dom.click(grid.$buttons.find('button.grid_arrow_previous'));
        assert.strictEqual(grid.model.getContext().grid_anchor, '2017-01-24', 'the grid anchor should move 7 days before the current one since we are in week range.');
        assert.strictEqual(grid.model.getContext().grid_range, 'week', 'the grid range should be "week".');
        await testUtils.dom.click($monthRangeButton);
        assert.hasClass($monthRangeButton,'active', 'current range should be month one.');
        assert.strictEqual(grid.model.getContext().grid_anchor, '2017-01-31',
            'Since with the month range, the current day is in the range, the grid anchor should be the current date and not 7 days before the current one.');
        assert.strictEqual(grid.model.getContext().grid_range, 'month', 'the grid range should be "month".');
        grid.destroy();
    });

    QUnit.test('display the empty grid without None line when there is no data', async function (assert) {

        this.data['analytic.line'].records = [];

        this.arch = `<grid string="Timesheet By Project" adjustment="object" adjust_name="adjust_grid">
                <field name="project_id" type="row" section="1"/>
                <field name="task_id" type="row"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                    <range name="month" string="Month" span="month" step="day"/>
                </field>
                <field name="unit_amount" type="measure" widget="float_time"/>
            </grid>`;

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: this.arch,
            currentDate: "2016-01-24",
        });

        assert.strictEqual(grid.$('.o_grid_section:eq(0) th').length, 0,
            "should not add None row");

        grid.destroy();
    });

    QUnit.test('ensure the "None" is displayed in multi-level groupby', async function (assert) {
        this.data['analytic.line'].fields = Object.assign({}, this.data['analytic.line'].fields, {
            employee_id: {string: "Employee", type: "many2one", relation: "employee"}
        });
        this.data['analytic.line'].records = [{ id: 1, project_id: 31, date: "2017-01-24", unit_amount: 2.5 }];
        this.data['employee'] = {
            fields : {
                name: {string: "Task Name", type: "char"}
            },
        };

        const grid = await createView({
            View: GridView,
            model: 'analytic.line',
            data: this.data,
            arch: '<grid string="Timesheet By Project">' +
                    '<field name="project_id" type="row" section="1"/>' +
                    '<field name="task_id" type="row"/>' +
                    '<field name="date" type="col">' +
                        '<range name="week" string="Week" span="week" step="day"/>' +
                    '</field>'+
                    '<field name="unit_amount" type="measure" widget="float_time"/>' +
                '</grid>',
            groupBy: ["task_id", "employee_id"],
            currentDate: "2017-01-25",
        });

        assert.strictEqual(grid.$('tr:eq(1) th').text(), 'None',
            "'None' should be shown in multi-level groupby"
        );

        grid.destroy();
    });

});
});
