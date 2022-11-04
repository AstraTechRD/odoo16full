/** @odoo-module */

import { Domain } from '@web/core/domain';
import { removeDomainLeaf } from '@web_gantt/js/gantt_controller';

QUnit.module('WebGantt > RemoveDomainLeaf');

QUnit.test('Remove leaf in domain.', function (assert) {
    let domain = [
        ['start_datetime', '!=', false], ['end_datetime', '!=', false],
        ['sale_line_id', '!=', false],
    ];
    const keysToRemove = ['start_datetime', 'end_datetime'];
    let newDomain = removeDomainLeaf(domain, keysToRemove);
    let expectedDomain = new Domain([
        '&', ...Domain.TRUE.toList({}), ...Domain.TRUE.toList({}),
        ['sale_line_id', '!=', false],
    ]);
    assert.deepEqual(
        newDomain.toList({}),
        expectedDomain.toList({}),
    );
    domain = [
        '|', ['role_id', '=', false],
            '&', ['resource_id', '!=', false], ['start_datetime', '=', false],
        ['sale_line_id', '!=', false],
    ];
    newDomain = removeDomainLeaf(domain, keysToRemove);
    expectedDomain = new Domain([
        '|', ['role_id', '=', false],
            '&', ['resource_id', '!=', false], ...Domain.TRUE.toList({}),
        ['sale_line_id', '!=', false],
    ]);
    assert.deepEqual(
        newDomain.toList({}),
        expectedDomain.toList({}),
    );
    domain = [
        '|', ['start_datetime', '=', false], ['end_datetime', '=', false],
        ['sale_line_id', '!=', false],
    ];
    newDomain = removeDomainLeaf(domain, keysToRemove);
    expectedDomain = new Domain([
        ...Domain.TRUE.toList({}),
        ['sale_line_id', '!=', false],
    ]);
    assert.deepEqual(
        newDomain.toList({}),
        expectedDomain.toList({}),
    );
});
