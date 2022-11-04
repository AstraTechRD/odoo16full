/** @odoo-module */

import { Domain } from '@web/core/domain';
import { createView } from 'web.test_utils';
import PlanningView from 'planning.PlanningGanttView';

const actualDate = new Date(2021, 9, 10, 8, 0, 0);
const initialDate = new Date(actualDate.getTime() - actualDate.getTimezoneOffset() * 60 * 1000);
const ganttViewParams = {
    arch: `<gantt date_start="start_datetime" date_stop="end_datetime" default_scale="week"/>`,
    domain: Domain.FALSE,
    model: 'planning.slot',
    viewOptions: { initialDate },
};

QUnit.module('SalePlanning > GanttView', {
    async beforeEach() {
        ganttViewParams.data = {
            'planning.slot': {
                fields: {
                    id: { string: 'ID', type: 'integer' },
                    role_id: { string: 'Role', type: 'many2one', relation: 'planning.role' },
                    sale_line_id: { string: 'Sale Order Item', type: 'many2one', relation: 'sale.order.line' },
                    resource_id: { string: 'Resource', type: 'many2one', relation: 'resource.resource' },
                    start_datetime: { string: 'Start Datetime', type: 'datetime' },
                    end_datetime: { string: 'End Datetime', type: 'datetime' },
                },
                records: [
                    {
                        id: 1,
                        role_id: 1,
                        sale_line_id: 1,
                        resource_id: false,
                        start_datetime: '2021-10-12 08:00:00',
                        end_datetime: '2021-10-12 12:00:00',
                    },
                ],
            },
            'planning.role': {
                fields: {
                    id: { string: 'ID', type: 'integer' },
                    name: { string: 'Name', type: 'char' },
                },
                records: [
                    { 'id': 1, name: 'Developer' },
                    { 'id': 2, name: 'Support Tech' },
                ],
            },
            'sale.order.line': {
                fields: {
                    id: { string: 'ID', type: 'integer' },
                    name: { string: 'Product Name', type: 'char' },
                },
                records: [
                    { id: 1, name: 'Computer Configuration' },
                ],
            }
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
    }
});

QUnit.test('Process domain for plan dialog', async function (assert) {
    assert.expect(3);

    const actionDomain = [['start_datetime', '!=', false], ['end_datetime', '!=', false]];
    const gantt = await createView({ ...ganttViewParams, domain: actionDomain, View: PlanningView });

    const state = gantt.model.get();
    gantt.actionDomain = actionDomain;
    let expectedDomain = Domain.and([
        Domain.and([
            new Domain(['&', ...Domain.TRUE.toList({}), ...Domain.TRUE.toList({})]),
            ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]],
        ]),
        [['sale_line_id', '!=', false]],
    ]);
    assert.deepEqual(gantt._getPlanDialogDomain(state), expectedDomain.toList({}));
    gantt.actionDomain = ['|', ['role_id', '=', false], '&', ['resource_id', '!=', false], ['start_datetime', '=', false]];
    expectedDomain = Domain.and([
        Domain.and([
            new Domain([
                '|', ['role_id', '=', false],
                    '&', ['resource_id', '!=', false], ...Domain.TRUE.toList({}),
            ]),
            ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]],
        ]),
        [['sale_line_id', '!=', false]],
    ]);
    assert.deepEqual(gantt._getPlanDialogDomain(state), expectedDomain.toList({}));
    gantt.actionDomain = ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]];
    expectedDomain = Domain.and([
        Domain.and([
            Domain.TRUE,
            ['|', ['start_datetime', '=', false], ['end_datetime', '=', false]],
        ]),
        [['sale_line_id', '!=', false]],
    ]);
    assert.deepEqual(gantt._getPlanDialogDomain(state), expectedDomain.toList({}));

    gantt.destroy();
});
