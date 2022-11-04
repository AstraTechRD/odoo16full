/** @odoo-module */

import testUtils, { createView } from "web.test_utils";
import { Domain } from "@web/core/domain";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import GanttView from "@web_gantt/js/gantt_view";
import GanttRenderer from "@web_gantt/js/gantt_renderer";
import GanttController from "@web_gantt/js/gantt_controller";

/**
 * As the rendering of the connectors is made after the gantt rendering is injected in the dom and as the connectors
 * are an owl component that needs to be mounted (async), we have no control on when they will actually be generated.
 * For that reason we had to create the testPromise and extend both TaskGanttConnectorRenderer and TaskGanttConnectorView.
* */
let testPromise = testUtils.makeTestPromise();
const TestGanttRenderer = GanttRenderer.extend({
    /**
     * @override
    */
    async updateConnectorContainerComponent() {
        await this._super(...arguments);
        return testPromise.resolve();
    }
});
const TestGanttView = GanttView.extend({
    config: Object.assign({}, GanttView.prototype.config, {
        Renderer: TestGanttRenderer,
    })
});

const actualDate = new Date(2021, 9, 10, 8, 0, 0);
const initialDate = new Date(actualDate.getTime() - actualDate.getTimezoneOffset() * 60 * 1000);
const ganttViewParams = {
    arch: `<gantt date_start="planned_date_begin" date_stop="planned_date_end" default_scale="month" dependency_field="depend_on_ids"/>`,
    domain: Domain.FALSE,
    model: 'project.task',
    viewOptions: {initialDate},
};

/**
 * Returns the connector dict associated with the provided gantt
 *
 * @param gantt
 * @return {Object} a dict of:
 *      - Keys:
 *          masterTaskId|masterTaskUserId|taskId|taskUserId
 *      - Values:
 *          connector
 */
function getConnectorsDict(gantt) {
    const connectorsDict = { };
    for (const connector of Object.values(gantt.renderer._connectors)) {
        const connector_data = connector.data;
        const masterUserId = JSON.parse(connector_data.masterRowId)[0].user_ids[0] || 0;
        const slaveUserId = JSON.parse(connector_data.slaveRowId)[0].user_ids[0] || 0;
        const testKey = `${connector_data.masterId}|${masterUserId}|${connector_data.slaveId}|${slaveUserId}`;
        connectorsDict[testKey] = connector;
    }
    return connectorsDict;
}

const CSS = {
    SELECTOR: {
        CONNECTOR: 'svg.o_connector',
        CONNECTOR_CONTAINER: '.o_connector_container',
        CONNECTOR_CREATOR_BULLET: '.o_connector_creator_bullet',
        CONNECTOR_CREATOR_WRAPPER: '.o_connector_creator_wrapper',
        CONNECTOR_STROKE: '.o_connector_stroke',
        CONNECTOR_STROKE_BUTTON: '.o_connector_stroke_button',
        CONNECTOR_STROKE_BUTTONS: '.o_connector_stroke_buttons',
        CONNECTOR_STROKE_RESCHEDULE_BUTTON: '.o_connector_stroke_reschedule_button',
        CONNECTOR_STROKE_REMOVE_BUTTON: '.o_connector_stroke_remove_button',
        INVISIBLE: '.invisible',
        PILL: '.o_gantt_pill',
    },
    CLASS: {
        CONNECTOR_HOVERED: 'o_connector_hovered',
        PILL_HIGHLIGHT: 'highlight',
    },
};

QUnit.module('LegacyViews > GanttView (legacy) > Gantt Dependency', {
    async beforeEach() {
        this.initialPopoverDefaultAnimation = Popover.Default.animation;
        Popover.Default.animation = false;

        testPromise = testUtils.makeTestPromise();
        ganttViewParams.data = {
            'project.task': {
                fields: {
                    id: { string: 'ID', type: 'integer' },
                    name: { string: 'Name', type: 'char' },
                    planned_date_begin: { string: 'Start Date', type: 'datetime' },
                    planned_date_end: { string: 'Stop Date', type: 'datetime' },
                    project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                    user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                    allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                    depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
                    display_warning_dependency_in_gantt: { string: 'Display warning dependency in Gantt', type: "boolean", default: true },
                },
                records: [
                    {
                        id: 1,
                        name: 'Task 1',
                        planned_date_begin: '2021-10-11 18:30:00',
                        planned_date_end: '2021-10-11 19:29:59',
                        project_id: 1,
                        user_ids: [1],
                        depend_on_ids: [],
                    },
                    {
                        id: 2,
                        name: 'Task 2',
                        planned_date_begin: '2021-10-12 11:30:00',
                        planned_date_end: '2021-10-12 12:29:59',
                        project_id: 1,
                        user_ids: [1],
                        depend_on_ids: [1],
                    },
                ],
            },
            'project.project': {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 1, name: 'Project 1'},
                ],
            },
            'res.users': {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 1, name: 'User 1'},
                ],
            },
        };
        ganttViewParams.mockRPCHook = function (route, args) {
            return null;
        };
        ganttViewParams.mockRPC = function (route, args) {
            const prom = ganttViewParams.mockRPCHook(route, args);
            if (prom !== null) {
                return prom;
            } else {
                return this._super.apply(this, arguments);
            }
        };
        ganttViewParams.View = TestGanttView;
    },
    async afterEach() {
        Popover.Default.animation = this.initialPopoverDefaultAnimation;
    },
});

QUnit.test('Connectors are correctly computed and rendered.', async function (assert) {
    /**
     * This test checks that:
     *     - That the connector is part of the props and both its props color is the expected one (=> 2 * testKeys.length tests).
     *     - There is no other connector than the one expected.
     *     - All connectors are rendered.
     */

    /**
     * Dict used to run all tests in one loop.
     *
     * - Keys:
     *      masterTaskId|masterTaskUserId|taskId|taskUserId
     * - Values:
     *      n 'normal', w 'warning or e 'error'
     *
     * =>  Check that there is a connector between masterTaskId from group masterTaskUserId and taskId from group taskUserId with normal|error color.
     */
    const tests = {
        '1|1|2|1': 'n',
        '1|1|2|3': 'n',
        '2|1|3|0': 'n',
        '2|3|3|0': 'n',
        '2|1|4|2': 'n',
        '2|3|4|3': 'n',
        '4|2|6|1': 'n',
        '4|3|6|3': 'n',
        '5|0|6|1': 'n',
        '5|0|6|3': 'n',
        '6|1|7|1': 'n',
        '6|1|7|2': 'n',
        '6|3|7|2': 'n',
        '6|3|7|3': 'n',
        '7|1|8|1': 'n',
        '7|2|8|1': 'n',
        '7|2|8|3': 'n',
        '7|3|8|3': 'n',
        '8|1|9|2': 'n',
        '8|3|9|2': 'n',
        '10|2|11|2': 'e',
        '12|2|13|2': 'w',
    };

    assert.expect(3 * Object.keys(tests).length + 2);

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-11 18:30:00',
                    planned_date_end: '2021-10-11 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
                {
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-12 11:30:00',
                    planned_date_end: '2021-10-12 12:29:59',
                    project_id: 1,
                    user_ids: [1, 3],
                    depend_on_ids: [1],
                },
                {
                    id: 3,
                    name: 'Task 3',
                    planned_date_begin: '2021-10-13 06:30:00',
                    planned_date_end: '2021-10-13 07:29:59',
                    project_id: 1,
                    user_ids: [],
                    depend_on_ids: [2],
                },
                {
                    id: 4,
                    name: 'Task 4',
                    planned_date_begin: '2021-10-14 22:30:00',
                    planned_date_end: '2021-10-14 23:29:59',
                    project_id: 1,
                    user_ids: [2, 3],
                    depend_on_ids: [2],
                },
                {
                    id: 5,
                    name: 'Task 5',
                    planned_date_begin: '2021-10-15 01:53:10',
                    planned_date_end: '2021-10-15 02:34:34',
                    project_id: 1,
                    user_ids: [],
                    depend_on_ids: [],
                },
                {
                    id: 6,
                    name: 'Task 6',
                    planned_date_begin: '2021-10-16 23:00:00',
                    planned_date_end: '2021-10-16 23:21:01',
                    project_id: 1,
                    user_ids: [1, 3],
                    depend_on_ids: [4, 5],
                },
                {
                    id: 7,
                    name: 'Task 7',
                    planned_date_begin: '2021-10-17 10:30:12',
                    planned_date_end: '2021-10-17 11:29:59',
                    project_id: 1,
                    user_ids: [1, 2, 3],
                    depend_on_ids: [6],
                },
                {
                    id: 8,
                    name: 'Task 8',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [1, 3],
                    depend_on_ids: [7],
                },
                {
                    id: 9,
                    name: 'Task 9',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [8],
                },
                {
                    id: 10,
                    name: 'Task 10',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                },
                {
                    id: 11,
                    name: 'Task 11',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [10],
                },
                {
                    id: 12,
                    name: 'Task 12',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                },
                {
                    id: 13,
                    name: 'Task 13',
                    planned_date_begin: '2021-10-18 07:29:59',
                    planned_date_end: '2021-10-20 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [12],
                },
            ],
        },
        'project.project': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'Project 1' },
            ],
        },
        'res.users': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'User 1' },
                { id: 2, name: 'User 2' },
                { id: 3, name: 'User 3' },
                { id: 4, name: 'User 4' },
            ],
        },
    };

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids'] });
    registerCleanup(gantt.destroy);
    await testPromise;

    const connectorsDict = getConnectorsDict(gantt);

    const connectorContainer = gantt.el.querySelector(CSS.SELECTOR.CONNECTOR_CONTAINER);
    const connectorsDictCopy = { ...connectorsDict };
    for (const [test_key, colorCode] of Object.entries(tests)) {
        const [masterTaskId, masterTaskUserId, taskId, taskUserId] = test_key.split('|');
        assert.ok(test_key in connectorsDict, `Connector between task ${masterTaskId} from group user ${masterTaskUserId} and task ${taskId} from group user ${taskUserId} should be present.`);

        let color;
        let connectorPropsColorMatch;
        let colorMessage;
        if (colorCode === 'n') {
            color = gantt.renderer._connectorsStrokeColors.stroke;
            connectorPropsColorMatch = !connectorsDict[test_key].style
                || !connectorsDict[test_key].style.stroke
                || !connectorsDict[test_key].style.stroke.color
                || connectorsDict[test_key].style.stroke.color === color;
            colorMessage = 'Connector props style should be the default one';
        } else {
            switch (colorCode) {
                case 'w':
                    color = gantt.renderer._connectorsStrokeWarningColors.stroke;
                    colorMessage = 'Connector props style should be the warning one';
                    break;
                case 'e':
                    color = gantt.renderer._connectorsStrokeErrorColors.stroke;
                    colorMessage = 'Connector props style should be the error one';
                    break;
            }
            connectorPropsColorMatch = connectorsDict[test_key].style.stroke.color === color;
        }
        const connector_stroke = connectorContainer.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="${connectorsDict[test_key].id}"] ${CSS.SELECTOR.CONNECTOR_STROKE}`);
        assert.equal(connector_stroke.getAttribute('stroke'), color);
        assert.ok(connectorPropsColorMatch, colorMessage);
        delete connectorsDictCopy[test_key];
    }

    assert.notOk(Object.keys(connectorsDictCopy).length, 'There should not be more connectors than expected.');
    assert.equal(gantt.el.querySelectorAll(CSS.SELECTOR.CONNECTOR).length, Object.keys(tests).length, 'All connectors should be rendered.');
});

QUnit.test('Connectors are rendered according to _shouldRenderRecordConnectors.', async function (assert) {
    /**
     * This test checks that _shouldRenderRecordConnectors effectively allows to prevent connectors to be rendered
     * for records the function would return false for.
     */

    assert.expect(1);

    testUtils.mock.patch(TestGanttRenderer, {
        _shouldRenderRecordConnectors(record) {
            return record.id !== 1;
        },
    });

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-11 18:30:00',
                    planned_date_end: '2021-10-11 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
                {
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-12 11:30:00',
                    planned_date_end: '2021-10-12 12:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [1],
                },
                {
                    id: 3,
                    name: 'Task 3',
                    planned_date_begin: '2021-10-13 06:30:00',
                    planned_date_end: '2021-10-13 07:29:59',
                    project_id: 1,
                    user_ids: [],
                    depend_on_ids: [1,2],
                },
            ],
        },
        'project.project': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'Project 1' },
            ],
        },
        'res.users': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'User 1' },
                { id: 2, name: 'User 2' },
                { id: 3, name: 'User 3' },
                { id: 4, name: 'User 4' },
            ],
        },
    };

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids'] });
    registerCleanup(gantt.destroy);
    await testPromise;

    const connectorsDict = getConnectorsDict(gantt);
    assert.deepEqual(Object.keys(connectorsDict), ['2|1|3|0'], 'The only rendered connector should be the one from task_id 2 to task_id 3');

    testUtils.mock.unpatch(TestGanttRenderer);
});

QUnit.test('Connectors are correctly computed and rendered when collapse_first_level is active.', async function (assert) {
    /**
     * This test checks that the connectors are correctly drew when collapse_first_level is active.
     */

    assert.expect(9);

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-11 18:30:00',
                    planned_date_end: '2021-10-11 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
                {
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-12 11:30:00',
                    planned_date_end: '2021-10-12 12:29:59',
                    project_id: 1,
                    user_ids: [1, 3],
                    depend_on_ids: [1],
                },
                {
                    id: 3,
                    name: 'Task 3',
                    planned_date_begin: '2021-10-13 06:30:00',
                    planned_date_end: '2021-10-13 07:29:59',
                    project_id: 1,
                    user_ids: [],
                    depend_on_ids: [2],
                },
                {
                    id: 4,
                    name: 'Task 4',
                    planned_date_begin: '2021-10-14 22:30:00',
                    planned_date_end: '2021-10-14 23:29:59',
                    project_id: 1,
                    user_ids: [2, 3],
                    depend_on_ids: [2],
                },
                {
                    id: 5,
                    name: 'Task 5',
                    planned_date_begin: '2021-10-15 01:53:10',
                    planned_date_end: '2021-10-15 02:34:34',
                    project_id: 1,
                    user_ids: [],
                    depend_on_ids: [],
                },
                {
                    id: 6,
                    name: 'Task 6',
                    planned_date_begin: '2021-10-16 23:00:00',
                    planned_date_end: '2021-10-16 23:21:01',
                    project_id: 1,
                    user_ids: [1, 3],
                    depend_on_ids: [4, 5],
                },
                {
                    id: 7,
                    name: 'Task 7',
                    planned_date_begin: '2021-10-17 10:30:12',
                    planned_date_end: '2021-10-17 11:29:59',
                    project_id: 1,
                    user_ids: [1, 2, 3],
                    depend_on_ids: [6],
                },
                {
                    id: 8,
                    name: 'Task 8',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [1, 3],
                    depend_on_ids: [7],
                },
                {
                    id: 9,
                    name: 'Task 9',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [8],
                },
                {
                    id: 10,
                    name: 'Task 10',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                },
                {
                    id: 11,
                    name: 'Task 11',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [10],
                },
                {
                    id: 12,
                    name: 'Task 12',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                },
                {
                    id: 13,
                    name: 'Task 13',
                    planned_date_begin: '2021-10-18 07:29:59',
                    planned_date_end: '2021-10-20 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [12],
                },
            ],
        },
        'project.project': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'Project 1' },
            ],
        },
        'res.users': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'User 1' },
                { id: 2, name: 'User 2' },
                { id: 3, name: 'User 3' },
                { id: 4, name: 'User 4' },
            ],
        },
    };

    const ganttViewParamsWithCollapse = {
        ...ganttViewParams,
        ...{ arch: ganttViewParams.arch.replace('/>', ' collapse_first_level="1"/>') }
    };
    const gantt = await createView({ ...ganttViewParamsWithCollapse, groupBy: ['user_ids'] });
    registerCleanup(gantt.destroy);
    await testPromise;

    assert.equal(gantt.el.querySelectorAll('.o_gantt_row_group.open').length, 4, '`collapse_first_level` is activated.');

    function getConnectorCounts() {
        return gantt.el.querySelectorAll('.o_connector').length;
    }

    let connectorsCount = getConnectorCounts();
    assert.equal(connectorsCount, 22, 'All connectors are drawn.');

    testPromise = testUtils.makeTestPromise();
    gantt.el.querySelector('.o_gantt_row_group.open[data-row-id^="[{\\"user_ids\\":[1,\\"User 1\\"]}]"]').click();
    await testPromise;
    connectorsCount = getConnectorCounts();
    assert.ok(gantt.el.querySelector('.o_gantt_row_group:not(.open)[data-row-id^="[{\\"user_ids\\":[1,\\"User 1\\"]}]"]'), 'Group has been closed.');
    assert.equal(connectorsCount, 13, 'Only connectors between open groups are drawn.');

    testPromise = testUtils.makeTestPromise();
    gantt.el.querySelector('.o_gantt_row_group:not(.open)[data-row-id^="[{\\"user_ids\\":[1,\\"User 1\\"]}]"]').click();
    await testPromise;
    connectorsCount = getConnectorCounts();
    assert.equal(connectorsCount, 22, 'All connectors are drawn after having reopen the only closed group.');

    testPromise = testUtils.makeTestPromise();
    gantt.el.querySelector('.o_gantt_row_group.open[data-row-id^="[{\\"user_ids\\":[1,\\"User 1\\"]}]"]').click();
    await testPromise;
    connectorsCount = getConnectorCounts();
    assert.equal(connectorsCount, 13, 'Only connectors between open groups are drawn.');

    testPromise = testUtils.makeTestPromise();
    gantt.el.querySelector('.o_gantt_row_group.open[data-row-id^="[{\\"user_ids\\":[2,\\"User 2\\"]}]"]').click();
    await testPromise;
    connectorsCount = getConnectorCounts();
    assert.equal(connectorsCount, 6, 'Only connectors between open groups are drawn.');

    testPromise = testUtils.makeTestPromise();
    gantt.el.querySelector('.o_gantt_row_group.open[data-row-id^="[{\\"user_ids\\":false}]"]').click();
    await testPromise;
    connectorsCount = getConnectorCounts();
    assert.equal(connectorsCount, 4, 'Only connectors between open groups are drawn.');

    testPromise = testUtils.makeTestPromise();
    gantt.el.querySelector('.o_gantt_row_group.open[data-row-id^="[{\\"user_ids\\":[3,\\"User 3\\"]}]"]').click();
    await testPromise;
    connectorsCount = getConnectorCounts();
    assert.equal(connectorsCount, 0, 'Only connectors between open groups are drawn.');
});

QUnit.test('Connector hovered state is triggered and color is set accordingly.', async function (assert) {
    /**
     * This test checks that:
     *     - The o_connector_hovered class is triggered according to the hover of the connector.
     *     - The color of the connector is set according to the provided styles.
     */

    assert.expect(4);

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    const connectorContainer = gantt.el.querySelector(CSS.SELECTOR.CONNECTOR_CONTAINER);
    let connector = connectorContainer.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="1"]`);
    let connector_stroke = connector.querySelector(CSS.SELECTOR.CONNECTOR_STROKE);

    assert.notOk(connector.classList.contains(CSS.CLASS.CONNECTOR_HOVERED), "Connectors that are not hovered don't contain the o_connector_hovered class.");
    assert.equal(connector_stroke.getAttribute('stroke'), gantt.renderer._connectorsStrokeColors.stroke);
    await testUtils.dom.triggerMouseEvent(connector, "mouseover");
    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();
    connector = connectorContainer.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="1"]`);
    connector_stroke = connector.querySelector(CSS.SELECTOR.CONNECTOR_STROKE);
    assert.ok(connector.classList.contains(CSS.CLASS.CONNECTOR_HOVERED), 'Hovered connectors contain the o_connector_hovered class');
    assert.equal(connector_stroke.getAttribute('stroke'), gantt.renderer._connectorsStrokeColors.hoveredStroke);
});

QUnit.test('Buttons are displayed when hovering a connector.', async function (assert) {

    assert.expect(2);

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    const connectorContainer = gantt.el.querySelector(CSS.SELECTOR.CONNECTOR_CONTAINER);
    const connector = connectorContainer.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="1"]`);

    assert.ok(connector.querySelector(CSS.SELECTOR.CONNECTOR_STROKE_BUTTON) === null, "Connectors that are not hovered don't display buttons.");
    await testUtils.dom.triggerMouseEvent(connector, "mouseover");
    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();
    assert.ok(connector.querySelector(CSS.SELECTOR.CONNECTOR_STROKE_BUTTON) !== null, "Connectors that are hovered display buttons.");
});

QUnit.test('Connector container is re-rendered.', async function (assert) {

    assert.expect(1);

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    testPromise = testUtils.makeTestPromise();
    document.querySelector('button.o_gantt_button_next').click();
    await testPromise;

    assert.strictEqual(
        document.querySelectorAll(`${CSS.SELECTOR.CONNECTOR_CONTAINER}`).length,
        1,
        "there should be a connector container."
    );
});

/**
 * We need to prevent the reload that is triggered after the rpc call to web_gantt_reschedule as it was
 * causing race conditions.
 */
const TestConnectorButtonRPCGanttController = GanttController.extend({
    reload() { },
});

// Connector's buttons RPC calls have been tested one by one as they trigger a reload of the view which
// was systematically causing the following test to fail.
async function testConnectorButtonRPC(assert, createButtonSelector, expectedStep) {
    assert.expect(2);

    ganttViewParams.mockRPCHook = (route, args) => {
        if (args.model === 'project.task') {
            if (args.method === 'web_gantt_reschedule' || args.method === 'write') {
                const [rpc_arg1, rpc_arg2, rpc_arg3 = null] = args.args;
                assert.step(`${args.method}|${rpc_arg1}|${JSON.stringify(rpc_arg2)}${rpc_arg3 ? `|${rpc_arg3}` : ''}`);
                return Promise.resolve(true);
            }
        }
        return null;
    };

    ganttViewParams.View = ganttViewParams.View.extend({
        config: Object.assign({}, ganttViewParams.View.prototype.config, {
            Controller: TestConnectorButtonRPCGanttController,
        })
    });

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    const connectorContainer = gantt.el.querySelector(CSS.SELECTOR.CONNECTOR_CONTAINER);
    const connector = connectorContainer.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="1"]`);

    await testUtils.dom.triggerMouseEvent(connector, "mouseover");
    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();

    await testUtils.dom.click(connector.querySelector(createButtonSelector));
    assert.verifySteps([expectedStep]);
}

QUnit.test('Correct RPC is called on connector buttons click.', async function (assert) {
    await testConnectorButtonRPC(
        assert,
        `${CSS.SELECTOR.CONNECTOR_STROKE_REMOVE_BUTTON}`,
        'write|2|{"depend_on_ids":[[3,1,false]]}'
    );
});

QUnit.test('Correct RPC is called on connector buttons click.', async function (assert) {
    await testConnectorButtonRPC(
        assert,
        `${CSS.SELECTOR.CONNECTOR_STROKE_RESCHEDULE_BUTTON}:first-of-type`,
        'web_gantt_reschedule|backward|1|2'
    );
});

QUnit.test('Correct RPC is called on connector buttons click.', async function (assert) {
    await testConnectorButtonRPC(
        assert,
        `${CSS.SELECTOR.CONNECTOR_STROKE_RESCHEDULE_BUTTON}:last-of-type`,
        'web_gantt_reschedule|forward|1|2'
    );
});

QUnit.test('Correct RPC is called on connector buttons click.', async function (assert) {

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
                display_warning_dependency_in_gantt: { string: 'Display warning dependency in Gantt', type: "boolean", default: true },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-12 11:30:00',
                    planned_date_end: '2021-10-12 12:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },{
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-11 18:30:00',
                    planned_date_end: '2021-10-11 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [1],
                },
            ],
        },
        'project.project': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'Project 1' },
            ],
        },
        'res.users': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'User 1' },
            ],
        },
    };

    await testConnectorButtonRPC(
        assert,
        `${CSS.SELECTOR.CONNECTOR_STROKE_RESCHEDULE_BUTTON}:first-of-type`,
        'web_gantt_reschedule|backward|1|2'
    );
});

QUnit.test('Correct RPC is called on connector buttons click.', async function (assert) {

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
                display_warning_dependency_in_gantt: { string: 'Display warning dependency in Gantt', type: "boolean", default: true },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-12 11:30:00',
                    planned_date_end: '2021-10-12 12:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },{
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-11 18:30:00',
                    planned_date_end: '2021-10-11 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [1],
                },
            ],
        },
        'project.project': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'Project 1' },
            ],
        },
        'res.users': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'User 1' },
            ],
        },
    };

    await testConnectorButtonRPC(
        assert,
        `${CSS.SELECTOR.CONNECTOR_STROKE_RESCHEDULE_BUTTON}:last-of-type`,
        'web_gantt_reschedule|forward|1|2'
    );
});

QUnit.test('Hovering a task pill, all the pills of the same task, and their related connectors are highlighted.', async function (assert) {
    /**
     * This test checks that:
     *     - When hovering a pill:
     *          _ The pill gets highlighted.
     *          - The connectorCreators get visible on that pill.
     *          - All the pills (in case of m2m grouping) representing the same task are highlighted but their connectorCreators are invisible.
     *          - All the connected connectors are highlighted.
     *          - The connectors that are not connected to the pill are not highlighted.
     *          - The connectors buttons are not visible on the highlighted connectors (note: the buttons should only become visible when the connector is hovered).
     */

    /**
     * Dict used to run all tests in one loop.
     *
     * - Keys:
     *      masterTaskId|masterTaskUserId|taskId|taskUserId
     * - Values:
     *      y 'expected to be hovered', n 'not expected to be hovered'
     *
     */
    const tests = {
        '1|1|2|1': 'y',
        '1|1|2|3': 'y',
        '2|1|3|0': 'y',
        '2|3|3|0': 'y',
        '2|1|4|2': 'y',
        '2|3|4|3': 'y',
        '10|2|11|2': 'n',
    };

    assert.expect(3 * Object.keys(tests).length + 8);

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
                display_warning_dependency_in_gantt: { string: 'Display warning dependency in Gantt', type: "boolean", default: true },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-11 18:30:00',
                    planned_date_end: '2021-10-10 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
                {
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-12 11:30:00',
                    planned_date_end: '2021-10-12 12:29:59',
                    project_id: 1,
                    user_ids: [1, 3],
                    depend_on_ids: [1],
                },
                {
                    id: 3,
                    name: 'Task 3',
                    planned_date_begin: '2021-10-13 06:30:00',
                    planned_date_end: '2021-10-13 07:29:59',
                    project_id: 1,
                    user_ids: [],
                    depend_on_ids: [2],
                },
                {
                    id: 4,
                    name: 'Task 4',
                    planned_date_begin: '2021-10-14 22:30:00',
                    planned_date_end: '2021-10-14 23:29:59',
                    project_id: 1,
                    user_ids: [2, 3],
                    depend_on_ids: [2],
                },
                {
                    id: 10,
                    name: 'Task 10',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                    display_warning_dependency_in_gantt: false,
                },
                {
                    id: 11,
                    name: 'Task 11',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [10],
                },
            ],
        },
        'project.project': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'Project 1' },
            ],
        },
        'res.users': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'User 1' },
                { id: 2, name: 'User 2' },
                { id: 3, name: 'User 3' },
            ],
        },
    };

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    const connectorsDict = getConnectorsDict(gantt);

    const connectorContainer = gantt.el.querySelector(CSS.SELECTOR.CONNECTOR_CONTAINER);
    const taskPills = gantt.el.querySelectorAll(`${CSS.SELECTOR.PILL}[data-id="2"]`);
    for (const taskPill of taskPills) {
        // The pills are not highlighted.
        assert.notOk(taskPill.classList.contains(CSS.CLASS.PILL_HIGHLIGHT), 'Pills should not be highlighted by default.');
        // Check that connector creators (little pills antennas) are not displayed.
        assert.ok(taskPill.parentElement.querySelectorAll(`${CSS.SELECTOR.CONNECTOR_CREATOR_WRAPPER}${CSS.SELECTOR.INVISIBLE}`).length === 2, 'Connector creators should be hidden by default.');
    }
    // Check that all connectors are not in hover state.
    for (const test_key in tests) {
        const connector = connectorContainer.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="${connectorsDict[test_key].id}"]`);
        assert.notOk(connector.classList.contains(CSS.CLASS.CONNECTOR_HOVERED), 'Connectors should not be in hovered state by default');
    }

    // Using jQuery trigger function as triggerEvent() for mouseenter does not bubble up and the event is not
    // triggered in the renderer.
    await $(taskPills[0]).trigger("mouseenter");
    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();
    for (const taskPill of taskPills) {
        // The pills are highlighted.
        assert.ok(taskPill.classList.contains(CSS.CLASS.PILL_HIGHLIGHT), 'Pills should be highlighted when hovered (or when pill of the same id is hovered (m2m grouping)).');
        // Check that connector creators (little pills antennas) are displayed (and only displayed) on the hovered pills.
        const querySelector = `${CSS.SELECTOR.CONNECTOR_CREATOR_WRAPPER}${taskPill != taskPills[0] ? CSS.SELECTOR.INVISIBLE : `:not(${CSS.SELECTOR.INVISIBLE})`}`;
        assert.ok(taskPill.parentElement.querySelectorAll(querySelector).length === 2, 'Connector creators should be displayed on the hovered pills and not on the others.');
    }
    // Check that all connectors are in the expected hover state.
    for (const [test_key, hoverEffectExpected] of Object.entries(tests)) {
        const connector = connectorContainer.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="${connectorsDict[test_key].id}"]`);
        if (hoverEffectExpected === 'y') {
            assert.ok(connector.classList.contains(CSS.CLASS.CONNECTOR_HOVERED), 'Connectors that are connected to an highlighted pill should be in a hover state.');
        } else {
            assert.notOk(connector.classList.contains(CSS.CLASS.CONNECTOR_HOVERED), 'Connectors that are not connected to an highlighted pill should not be in a hover state.');
        }
        assert.ok(connector.querySelector(CSS.SELECTOR.CONNECTOR_STROKE_BUTTON) === null, "Connectors that are not hovered don't display buttons, even if they are highlighted.");
    }

});

QUnit.test('Hovering a connector should cause the connected pills to get highlighted.', async function (assert) {
    assert.expect(3);

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    const connector = gantt.el.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="1"]`);
    let taskPills = gantt.el.querySelectorAll(`${CSS.SELECTOR.PILL}:not(.${CSS.CLASS.PILL_HIGHLIGHT})`);
    assert.equal(taskPills.length, 2, 'Pills should not be highlighted by default.');

    await testUtils.dom.triggerMouseEvent(connector, "mouseover");
    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();

    taskPills = gantt.el.querySelectorAll(`${CSS.SELECTOR.PILL}.${CSS.CLASS.PILL_HIGHLIGHT}`);
    assert.equal(taskPills.length, 2, 'Pills should be highlighted when linked connector is hovered.');
    // Check that connector creators (little pills antennas) are displayed (and only displayed) on the hovered pills.
    const querySelector = `${CSS.SELECTOR.CONNECTOR_CREATOR_WRAPPER}:not(${CSS.SELECTOR.INVISIBLE})`;
    assert.ok(gantt.el.querySelectorAll(querySelector).length === 0, 'Connector creators should not be displayed if the pill is not hovered.');

});

QUnit.test('Connectors are displayed behind pills, except on hover.', async function (assert) {
    assert.expect(2);

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
                display_warning_dependency_in_gantt: { string: 'Display warning dependency in Gantt', type: "boolean", default: true },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-01 18:30:00',
                    planned_date_end: '2021-10-02 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
                {
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-04 11:30:00',
                    planned_date_end: '2021-10-05 12:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
                {
                    id: 3,
                    name: 'Task 3',
                    planned_date_begin: '2021-10-15 06:30:00',
                    planned_date_end: '2021-10-15 07:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [1],
                },
            ],
        },
        'project.project': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'Project 1' },
            ],
        },
        'res.users': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
            },
            records: [
                { id: 1, name: 'User 1' },
            ],
        },
    };

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    // For this tests, we need the elements to be visible in the viewport.
    const viewElements = [...document.getElementById('qunit-fixture').children];
    viewElements.forEach(el => document.body.prepend(el));

    // As connectors have been generated based on the pills positions, we need to preserve the
    // previous width of the gantt view.
    const client = document.querySelector('.o_web_client');
    client.style.width = '1000px';

    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();

    const taskPill = gantt.el.querySelector(`${CSS.SELECTOR.PILL}[data-id="2"]`);

    const taskPillLocation = taskPill.getBoundingClientRect();
    const testLocationLeft = taskPillLocation.left + taskPill.offsetWidth/2;
    const testLocationTop = taskPillLocation.top + taskPill.offsetHeight/2;
    let test = document.elementFromPoint(testLocationLeft, testLocationTop);
    assert.deepEqual(test, taskPill, "taskPill position");

    const connector = gantt.el.querySelector(`${CSS.SELECTOR.CONNECTOR}[data-id="1"]`);
    await testUtils.dom.triggerMouseEvent(connector, "mouseover");
    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();
    test = document.elementFromPoint(taskPillLocation.left, testLocationTop);
    assert.deepEqual(test.closest(CSS.SELECTOR.CONNECTOR), connector, "connector position");

});

QUnit.test('Create a connector from the gantt view.', async function (assert) {

    assert.expect(2);

    ganttViewParams.data = {
        'project.task': {
            fields: {
                id: { string: 'ID', type: 'integer' },
                name: { string: 'Name', type: 'char' },
                planned_date_begin: { string: 'Start Date', type: 'datetime' },
                planned_date_end: { string: 'Stop Date', type: 'datetime' },
                project_id: { string: 'Project', type: 'many2one', relation: 'project.project' },
                user_ids: { string: 'Assignees', type: 'many2many', relation: 'res.users' },
                allow_task_dependencies: { string: 'Allow Task Dependencies', type: "boolean", default: true },
                depend_on_ids: { string: 'Depends on', type: 'one2many', relation: 'project.task' },
                display_warning_dependency_in_gantt: { string: 'Display warning dependency in Gantt', type: "boolean", default: true },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-11 18:30:00',
                    planned_date_end: '2021-10-11 19:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
                {
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-12 11:30:00',
                    planned_date_end: '2021-10-12 12:29:59',
                    project_id: 1,
                    user_ids: [1],
                    depend_on_ids: [],
                },
            ],
        },
        'project.project': {
            fields: {
                id: {string: 'ID', type: 'integer'},
                name: {string: 'Name', type: 'char'},
            },
            records: [
                {id: 1, name: 'Project 1'},
            ],
        },
        'res.users': {
            fields: {
                id: {string: 'ID', type: 'integer'},
                name: {string: 'Name', type: 'char'},
            },
            records: [
                {id: 1, name: 'User 1'},
            ],
        },
    };

    ganttViewParams.mockRPCHook = (route, args) => {
        if (args.model === 'project.task' && args.method === 'write') {
            const [rpc_arg1, rpc_arg2] = args.args;
            assert.step(`${args.method}|${rpc_arg1}|${JSON.stringify(rpc_arg2)}`);
            return Promise.resolve(true);
        }
        return null;
    };

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
    registerCleanup(gantt.destroy);
    await testPromise;

    let taskPill = gantt.el.querySelector(`${CSS.SELECTOR.PILL}[data-id="1"]`);
    await $(taskPill).trigger("mouseenter");
    await testUtils.nextTick();
    await testUtils.returnAfterNextAnimationFrame();

    const connectorCreator = taskPill.parentElement.querySelector(`${CSS.SELECTOR.CONNECTOR_CREATOR_WRAPPER}:not(${CSS.SELECTOR.INVISIBLE}) ${CSS.SELECTOR.CONNECTOR_CREATOR_BULLET}`);
    await testUtils.dom.triggerEvents(connectorCreator, "mousedown", { bubbles: true });

    taskPill = gantt.el.querySelectorAll(`${CSS.SELECTOR.PILL}[data-id="2"]`);
    await testUtils.dom.triggerEvents(taskPill, "mouseup", { bubbles: true });
    assert.verifySteps(['write|2|{"depend_on_ids":[[4,1,false]]}'], 'Connector ui creation from task 1 to task 2 should result in an rpc call on project.task write.');

});
