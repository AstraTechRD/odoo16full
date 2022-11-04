/** @odoo-module */

import { createView, makeTestPromise } from "web.test_utils";
import { Domain } from "@web/core/domain";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import TaskGanttView from "@project_enterprise/js/task_gantt_view";
import GanttRenderer from "@project_enterprise/js/task_gantt_renderer";

/**
 * As the rendering of the connectors is made after the gantt rendering is injected in the dom and as the connectors
 * are an owl component that needs to be mounted (async), we have no control on when they will actually be generated.
 * For that reason we had to create the testPromise and extend both TaskGanttConnectorRenderer and TaskGanttConnectorView.
* */
let testPromise = makeTestPromise();
const TestGanttRenderer = GanttRenderer.extend({
    /**
     * @override
    */
    async _mountConnectorContainer() {
        await this._super(...arguments);
        testPromise.resolve();
    }
});
const TestGanttView = TaskGanttView.extend({
    config: Object.assign({}, TaskGanttView.prototype.config, {
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

QUnit.module('Views > GanttView > Task Gantt Dependency', {
    async beforeEach() {
        testPromise = makeTestPromise();
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
            if (args.method === 'search_milestone_from_task') {
                return Promise.resolve([]);
            }
            const prom = ganttViewParams.mockRPCHook(route, args);
            if (prom !== null) {
                return prom;
            } else {
                return this._super.apply(this, arguments);
            }
        };
        ganttViewParams.View = TestGanttView;
    }
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
        '1|2|2|2': 'n',
        '3|2|4|2': 'n',
        '5|2|6|2': 'e',
        '7|2|8|2': 'w',
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
                display_warning_dependency_in_gantt: { string: 'Display warning dependency in Gantt', type: "boolean", default: true },
            },
            records: [
                {
                    id: 1,
                    name: 'Task 1',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                    display_warning_dependency_in_gantt: false,
                },
                {
                    id: 2,
                    name: 'Task 2',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [1],
                },
                {
                    id: 3,
                    name: 'Task 3',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                },
                {
                    id: 4,
                    name: 'Task 4',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [3],
                    display_warning_dependency_in_gantt: false,
                },
                {
                    id: 5,
                    name: 'Task 5',
                    planned_date_begin: '2021-10-19 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                },
                {
                    id: 6,
                    name: 'Task 6',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-18 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [5],
                },
                {
                    id: 7,
                    name: 'Task 7',
                    planned_date_begin: '2021-10-18 06:30:12',
                    planned_date_end: '2021-10-19 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [],
                },
                {
                    id: 8,
                    name: 'Task 8',
                    planned_date_begin: '2021-10-18 07:29:59',
                    planned_date_end: '2021-10-20 07:29:59',
                    project_id: 1,
                    user_ids: [2],
                    depend_on_ids: [7],
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

    const gantt = await createView({ ...ganttViewParams, groupBy: ['user_ids']});
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
