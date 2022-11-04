/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('approvals', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity', {}, function () {
QUnit.module('activity_tests.js');

QUnit.test('activity with approval to be made by logged user', async function (assert) {
    assert.expect(14);

    const pyEnv = await startServer();
    const approvalRequestId1 = pyEnv['approval.request'].create({});
    pyEnv['approval.approver'].create({
        request_id: approvalRequestId1,
        status: 'pending',
        user_id: pyEnv.currentUserId,
    });
    pyEnv['mail.activity'].create({
        can_write: true,
        res_id: approvalRequestId1,
        res_model: 'approval.request',
        user_id: pyEnv.currentUserId,
    });
    const { openView } = await start();
    await openView({
        res_model: 'approval.request',
        res_id: approvalRequestId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_sidebar',
        "should have activity sidebar"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_core',
        "should have activity core"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_user',
        "should have activity user"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_info',
        "should have activity info"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_note',
        "should not have activity note"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_details',
        "should not have activity details"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_mailTemplates',
        "should not have activity mail templates"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_editButton',
        "should not have activity Edit button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_cancelButton',
        "should not have activity Cancel button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_markDoneButton',
        "should not have activity Mark as Done button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_uploadButton',
        "should not have activity Upload button"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_approveButton',
        "should have approval approve button"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_refuseButton',
        "should have approval refuse button"
    );
});

QUnit.test('activity with approval to be made by another user', async function (assert) {
    assert.expect(16);

    const pyEnv = await startServer();
    const approvalRequestId1 = pyEnv['approval.request'].create({});
    const resUsersId1 = pyEnv['res.users'].create({});
    pyEnv['approval.approver'].create({
        request_id: approvalRequestId1,
        status: 'pending',
        user_id: resUsersId1,
    });
    pyEnv['mail.activity'].create({
        can_write: true,
        res_id: approvalRequestId1,
        res_model: 'approval.request',
        user_id: resUsersId1,
    });
    const { openView } = await start();
    await openView({
        res_model: 'approval.request',
        res_id: approvalRequestId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_sidebar',
        "should have activity sidebar"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_core',
        "should have activity core"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_user',
        "should have activity user"
    );
    assert.containsOnce(
        document.body,
        '.o_Activity_info',
        "should have activity info"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_note',
        "should not have activity note"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_details',
        "should not have activity details"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_mailTemplates',
        "should not have activity mail templates"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_editButton',
        "should not have activity Edit button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_cancelButton',
        "should not have activity Cancel button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_markDoneButton',
        "should not have activity Mark as Done button"
    );
    assert.containsNone(
        document.body,
        '.o_Activity_uploadButton',
        "should not have activity Upload button"
    );
    assert.containsNone(
        document.body,
        '.o_Approval_approveButton',
        "should not have approval approve button"
    );
    assert.containsNone(
        document.body,
        '.o_Approval_refuseButton',
        "should not have approval refuse button"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_toApproveText',
        "should contain 'To approve' text container"
    );
    assert.strictEqual(
        document.querySelector('.o_Approval_toApproveText').textContent.trim(),
        "To Approve",
        "should contain 'To approve' text"
    );
});

QUnit.test('approve approval', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const approvalRequestId1 = pyEnv['approval.request'].create({});
    pyEnv['approval.approver'].create({
        request_id: approvalRequestId1,
        status: 'pending',
        user_id: pyEnv.currentUserId,
    });
    pyEnv['mail.activity'].create({
        can_write: true,
        res_id: approvalRequestId1,
        res_model: 'approval.request',
        user_id: pyEnv.currentUserId,
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'action_approve') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], approvalRequestId1);
                assert.step('action_approve');
            }
        },
    });
    await openView({
        res_model: 'approval.request',
        res_id: approvalRequestId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_approveButton',
        "should have approval approve button"
    );

    document.querySelector('.o_Approval_approveButton').click();
    assert.verifySteps(['action_approve'], "Approve button should trigger the right rpc call");
});

QUnit.test('refuse approval', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const approvalRequestId1 = pyEnv['approval.request'].create({});
    pyEnv['approval.approver'].create({
        request_id: approvalRequestId1,
        status: 'pending',
        user_id: pyEnv.currentUserId,
    });
    pyEnv['mail.activity'].create({
        can_write: true,
        res_id: approvalRequestId1,
        res_model: 'approval.request',
        user_id: pyEnv.currentUserId,
    });
    const { openView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'action_refuse') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], approvalRequestId1);
                assert.step('action_refuse');
            }
        },
    });
    await openView({
        res_model: 'approval.request',
        res_id: approvalRequestId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Activity',
        "should have activity component"
    );
    assert.containsOnce(
        document.body,
        '.o_Approval_refuseButton',
        "should have approval refuse button"
    );

    document.querySelector('.o_Approval_refuseButton').click();
    assert.verifySteps(['action_refuse'], "Refuse button should trigger the right rpc call");
});

});
});
});
