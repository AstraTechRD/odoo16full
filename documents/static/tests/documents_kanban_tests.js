/** @odoo-module **/

import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { createDocumentsView as originalCreateDocumentsView, createDocumentsViewWithMessaging } from './documents_test_utils';
import { registry } from '@web/core/registry';
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { DocumentsKanbanRenderer } from "@documents/views/kanban/documents_kanban_renderer";
import { DocumentsInspector } from "@documents/views/inspector/documents_inspector";

import {
    afterNextRender,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import {
    toggleFilterMenu,
    toggleMenuItem,
    pagerNext,
    pagerPrevious,
} from "@web/../tests/search/helpers";

import testUtils from 'web.test_utils';
import {
    editInput,
    clickOpenedDropdownItem,
    clickOpenM2ODropdown,
    getFixture,
    nextTick,
    click,
    patchWithCleanup,
    triggerEvent,
} from '@web/../tests/helpers/utils';
import { str_to_datetime } from 'web.time';
import { session } from "@web/session";
import { browser, makeRAMLocalStorage } from "@web/core/browser/browser";

const serviceRegistry = registry.category("services");
const find = testUtils.dom.find;

function createDocumentsView(params) {
    return originalCreateDocumentsView({
        serverData: { models: pyEnv.getData(), views: {} },
        ...params,
    });
}

let target;
let pyEnv;

QUnit.module('documents', {}, function () {
QUnit.module('documents_kanban_tests.js', {
    async beforeEach() {
        serviceRegistry.add("file_upload", fileUploadService);
        serviceRegistry.add("documents_pdf_thumbnail", {
            start() {
                return {
                    enqueueRecords: () => {},
                };
            },
        });
        // navigator.clipboard.writeText is not always allowed during testing.
        patchWithCleanup(DocumentsInspector.prototype, {
            _writeInClipboard() {},
        });
        // Historically the inspector had the preview on the kanban, due to it being
        // controlled with a props we simply force the kanban view to also have it during the tests
        // to ensure that the functionality stays the same, while keeping the tests as is.
        patchWithCleanup(DocumentsKanbanRenderer.prototype, {
            getDocumentsInspectorProps() {
                const result = this._super(...arguments);
                result.withFilePreview = true;
                return result;
            },
        });
        this.ORIGINAL_CREATE_XHR = fileUploadService.createXhr;
        this.patchDocumentXHR = (mockedXHRs, customSend) => {
            fileUploadService.createXhr = () => {
                const xhr = new window.EventTarget();
                Object.assign(xhr, {
                    upload: new window.EventTarget(),
                    open() {},
                    send(data) { customSend && customSend(data); },
                });
                mockedXHRs.push(xhr);
                return xhr;
            };
        };
        pyEnv = await startServer();
        const resPartnerIds = pyEnv['res.partner'].create([
            { display_name: 'Hazard' },
            { display_name: 'Lukaku' },
            { display_name: 'De Bruyne' },
            { email: 'raoul@grosbedon.fr', name: 'Raoul Grosbedon' },
            { email: 'raoulette@grosbedon.fr', name: 'Raoulette Grosbedon' },
        ]);
        const resUsersIds = pyEnv['res.users'].create([
            { display_name: 'Hazard', partner_id: resPartnerIds[0] },
            { display_name: 'Lukaku', partner_id: resPartnerIds[1] },
            { display_name: 'De Bruyne', partner_id: resPartnerIds[2] }
        ]);
        const documentsFolderIds = pyEnv['documents.folder'].create([
            { name: 'Workspace1', description: '_F1-test-description_', has_write_access: true },
            { name: 'Workspace2', has_write_access: true },
        ]);
        documentsFolderIds.push(
            pyEnv['documents.folder'].create([
                { name: 'Workspace3', parent_folder_id: documentsFolderIds[0], has_write_access: true },
            ])
        );
        const [documentsFacetId1, documentsFacetId2] = pyEnv['documents.facet'].create([
            { name: 'Status', tooltip: 'A Status tooltip', sequence: 11 },
            { name: 'Priority', tooltip: 'A priority tooltip', sequence: 10 }]);
        const documentsTagIds = pyEnv['documents.tag'].create([
            { display_name: 'New', facet_id: documentsFacetId1, sequence: 11 },
            { display_name: 'Draft', facet_id: documentsFacetId1, sequence: 10 },
            { display_name: 'No stress', facet_id: documentsFacetId2, sequence: 10 },
        ]);
        const documentsWorkflowRuleIds = pyEnv['documents.workflow.rule'].create([
            { display_name: 'Convincing AI not to turn evil', note: 'Racing for AI Supremacy' },
            { display_name: 'Follow the white rabbit' },
            { display_name: 'Entangling superstrings' },
            { display_name: 'One record rule', limited_to_single_record: true },
        ]);
        const resFakeIds = pyEnv['res.fake'].create([{ name: 'fake1' }, { name: 'fake2' }]);
        const irAttachmentId1 = pyEnv['ir.attachment'].create({});
        const [documentsDocumentId1, documentsDocumentId2] = pyEnv['documents.document'].create([
            {
                activity_state: 'today', available_rule_ids: [documentsWorkflowRuleIds[0], documentsWorkflowRuleIds[1], documentsWorkflowRuleIds[3]],
                file_size: 30000, folder_id: documentsFolderIds[0], is_editable_attachment: true, name: 'yop', owner_id: resUsersIds[0],
                partner_id: resPartnerIds[1], res_id: resFakeIds[0], res_model: 'res.fake', res_model_name: 'Task', res_name: 'Write specs',
                tag_ids: [documentsTagIds[0], documentsTagIds[1]],
            },
            {
                available_rule_ids: [1], file_size: 20000, folder_id: documentsFolderIds[0], mimetype: 'application/pdf', name: 'blip',
                owner_id: resUsersIds[1], partner_id: resPartnerIds[1], res_id: resFakeIds[1], res_model: 'res.fake', res_model_name: 'Task',
                res_name: 'Write tests', tag_ids: [documentsTagIds[1]],
            },
        ]);
        pyEnv['documents.document'].create([
            {
                available_rule_ids: documentsWorkflowRuleIds, file_size: 15000, folder_id: documentsFolderIds[0], lock_uid: resUsersIds[2],
                name: 'gnap', owner_id: resUsersIds[1], partner_id: resPartnerIds[0], res_id: documentsDocumentId2, res_model: 'documents.document',
                res_model_name: 'Task', tag_ids: [documentsTagIds[0], documentsTagIds[1], documentsTagIds[2]],
            },
            {
                file_size: 10000, folder_id: documentsFolderIds[0], mimetype: 'image/png', name: 'burp', owner_id: resUsersIds[0],
                partner_id: resPartnerIds[2], res_id: irAttachmentId1, res_model: 'ir.attachment', res_model_name: 'Attachment',

            },
            {
                available_rule_ids: [documentsWorkflowRuleIds[0], documentsWorkflowRuleIds[1], documentsWorkflowRuleIds[3]], file_size: 40000,
                folder_id: documentsFolderIds[0], lock_uid: resUsersIds[0], name: 'zip', owner_id: resUsersIds[1], partner_id: resPartnerIds[1],
                tag_ids: documentsTagIds,
            },
            {
                file_size: 70000, folder_id: documentsFolderIds[1], name: 'pom', partner_id: resPartnerIds[2], res_id: documentsDocumentId1,
                res_model: 'documents.document', res_model_name: 'Document',
            },
            {
                active: false, file_size: 70000, folder_id: documentsFolderIds[0], name: 'wip', owner_id: resUsersIds[2], partner_id: resPartnerIds[2],
                res_id: irAttachmentId1, res_model: 'ir.attachment', res_model_name: 'Attachment',
            },
            {
                active: false, file_size: 20000, folder_id: documentsFolderIds[0], mimetype: 'text/plain', name: 'zorro', owner_id: resUsersIds[2],
                partner_id: resPartnerIds[2],
            },
        ]);
        setupViewRegistries();
        target = getFixture();
    },
    afterEach() {
        fileUploadService.createXhr = this.ORIGINAL_CREATE_XHR;
        pyEnv = undefined;
    },
}, function () {
    QUnit.test('kanban basic rendering', async function (assert) {
        assert.expect(25);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });
        assert.strictEqual(target.querySelector('header.active > .o_search_panel_label .o_search_panel_label_title').textContent.trim(), 'Workspace1',
            "the first selected record should be the first folder");
        assert.strictEqual(target.querySelector('header.active > .o_search_panel_counter').textContent.trim(), '5',
            "the first folder should have 5 as counter");
        assert.containsOnce(target, '.o_search_panel_category_value:contains(All) header',
            "Should only have a single all selector");

        await click(target, '.o_search_panel_category_value:nth-of-type(1) header');

        assert.ok(target.querySelector('.o_documents_kanban_upload').disabled,
            "the upload button should be disabled on global view");
        assert.ok(target.querySelector('.o_documents_kanban_url').disabled,
            "the upload url button should be disabled on global view");
        assert.ok(target.querySelector('.o_documents_kanban_request').disabled,
            "the request button should be disabled on global view");
        assert.ok(target.querySelector('.o_documents_kanban_share_domain').disabled,
            "the share button should be disabled on global view");

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 6,
            "should have 6 records in the renderer");
        assert.containsNone(target, '.o_documents_selector_tags',
            "should not display the tag navigation because no workspace is selected by default");

        await click(target, '.o_search_panel_category_value:nth-of-type(2) header');

        // check view layout
        assert.containsN(target, '.o_content > div', 3,
            "should have 3 columns");
        assert.containsOnce(target.querySelector('.o_content'), '> div.o_search_panel',
            "should have a 'documents selector' column");
        assert.containsOnce(target, '.o_content > .o_kanban_renderer',
            "should have a 'classical kanban view' column");
        assert.hasClass(target.querySelector('.o_kanban_renderer'), 'o_documents_kanban_view',
            "should have classname 'o_documents_kanban_view'");
        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 5,
            "should have 5 records in the renderer");
        assert.containsOnce(target, '.o_kanban_record:first .o_record_selector',
            "should have a 'selected' button");
        assert.containsOnce(target, '.o_content > .o_documents_inspector',
            "should have a 'document inspector' column");

        // check control panel buttons
        assert.containsOnce(target, '.o_cp_buttons .btn-primary');
        assert.strictEqual(target.querySelector('.o_cp_buttons .btn-primary').textContent.trim(), 'Upload',
            "should have a primary 'Upload' button");
        assert.ok(target.querySelector('.o_documents_kanban_upload').disabled === false,
            "the upload button should be enabled when a folder is selected");
        assert.containsOnce(target, '.o_cp_buttons button.o_documents_kanban_url',
            "should allow to save a URL");
        assert.ok(target.querySelector('.o_documents_kanban_url').disabled === false,
            "the upload url button should be enabled when a folder is selected");
        assert.strictEqual(target.querySelector('.o_cp_buttons button.o_documents_kanban_request').textContent.trim(), 'Request',
            "should have a primary 'request' button");
        assert.ok(target.querySelector('.o_documents_kanban_request').disabled === false,
            "the request button should be enabled when a folder is selected");
        assert.strictEqual(target.querySelector('.o_cp_buttons button.btn-secondary.o_documents_kanban_share_domain').textContent.trim(), 'Share',
            "should have a secondary 'Share' button");
        assert.ok(target.querySelector('.o_documents_kanban_share_domain').disabled === false,
            "the share button should be enabled when a folder is selected");
    });

    QUnit.test('can select records by clicking on the select icon', async function (assert) {
        assert.expect(6);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        const firstRecord = target.querySelector('.o_kanban_record');
        assert.doesNotHaveClass(firstRecord, 'o_record_selected',
        "first record should not be selected");
        await click(firstRecord, '.o_record_selector');
        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should be selected");

        const thirdRecord = target.querySelectorAll('.o_kanban_record')[2];
        assert.doesNotHaveClass(thirdRecord, 'o_record_selected',
            "third record should not be selected");
        await click(thirdRecord, '.o_record_selector');
        assert.hasClass(thirdRecord, 'o_record_selected',
            "third record should be selected");

        await click(firstRecord, '.o_record_selector');
        assert.doesNotHaveClass(firstRecord, 'o_record_selected',
            "first record should not be selected");
        assert.hasClass(thirdRecord, 'o_record_selected',
            "third record should be selected");
    });

    QUnit.test('can select records by clicking on them', async function (assert) {
        assert.expect(5);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                        </div>
                    </t></templates></kanban>`,
        });

        assert.containsNone(target, '.o_kanban_record.o_record_selected',
            "no record should be selected");

        const firstRecord = target.querySelector('.o_kanban_record');
        await click(firstRecord);
        assert.containsOnce(target, '.o_kanban_record.o_record_selected',
            "one record should be selected");
        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should be selected");

        const thirdRecord = target.querySelectorAll('.o_kanban_record')[2];
        await click(thirdRecord);
        assert.containsOnce(target, '.o_kanban_record.o_record_selected',
            "one record should be selected");
        assert.hasClass(thirdRecord, 'o_record_selected',
            "third record should be selected");
    });

    QUnit.test('can unselect a record', async function (assert) {
        assert.expect(3);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                        </div>
                    </t></templates></kanban>`,
        });

        assert.containsNone(target, '.o_kanban_record.o_record_selected');

        const firstRecord = target.querySelector('.o_kanban_record');
        await click(firstRecord);
        assert.hasClass(firstRecord, 'o_record_selected');

        await click(firstRecord);
        assert.containsNone(target, '.o_kanban_record.o_record_selected');
    });

    QUnit.test('can select records with keyboard navigation', async function (assert) {
        assert.expect(4);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                            <button name="some_method" type="object"/>
                        </div>
                    </t></templates></kanban>`,
        });

        patchWithCleanup(kanban.env.services.action, {
            doActionButton({ onClose }) {
                assert.ok(false, "should not trigger an 'execute_action' event");
                onClose();
            },
        });

        const firstRecord = target.querySelector('.o_kanban_record');
        assert.doesNotHaveClass(firstRecord, 'o_record_selected',
            "first record should not be selected");
        await triggerEvent(firstRecord, null, 'keydown', {
            key: "Enter",
        });
        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should be selected");

        const thirdRecord = target.querySelector('.o_kanban_record:nth-of-type(3)');
        await triggerEvent(thirdRecord, null, 'keydown', {
            key: "Enter",
        });
        assert.hasClass(thirdRecord, 'o_record_selected',
            "third record should be selected");
        assert.doesNotHaveClass(firstRecord, 'o_record_selected',
            "first record should no longer be selected");
    });

    QUnit.test('can multi select records with shift and ctrl', async function (assert) {
        assert.expect(6);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                        <button name="some_method" type="object"/>
                    </div>
                </t></templates></kanban>`,
        });

        const firstRecord = target.querySelector('.o_kanban_record');
        assert.doesNotHaveClass(firstRecord, 'o_record_selected',
            "first record should not be selected");
        await triggerEvent(firstRecord, null, 'keydown', {
            key: "Enter",
        });
        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should be selected");

        const thirdRecord = target.querySelectorAll('.o_kanban_record')[2];
        await triggerEvent(thirdRecord, null, 'keydown', {
            key: "Enter",
            shiftKey: true,
        });
        assert.hasClass(thirdRecord, 'o_record_selected',
            "third record should be selected (shift)");
        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should still be selected (shift)");

        await triggerEvent(firstRecord, null, 'keydown', {
            key: "Enter",
            ctrlKey: true
        });

        assert.hasClass(thirdRecord, 'o_record_selected',
            "third record should still be selected (ctrl)");
        assert.doesNotHaveClass(firstRecord, 'o_record_selected',
            "first record should no longer be selected (ctrl)");
    });

    QUnit.test('only visible selected records are kept after a reload', async function (assert) {
        assert.expect(6);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: '<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<i class="fa fa-circle-thin o_record_selector"/>' +
                        '<field name="name"/>' +
                        '<button name="some_method" type="object"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            searchViewArch: `
                    <search>
                        <filter name="owo" string="OwO" domain="[['name', '=', 'burp']]"/>
                    </search>`,
        });

        kanban.model.root.records.filter(rec => ['yop', 'burp', 'blip'].includes(rec.data.name)).forEach(rec => rec.toggleSelection(true));
        await nextTick();

        assert.containsN(target, '.o_record_selected', 3,
            "should have 3 selected records");
        assert.containsN(target, '.o_documents_inspector_preview .o_document_preview', 3,
            "should show 3 document previews in the DocumentsInspector");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "OwO");

        assert.containsOnce(target, '.o_record_selected',
            "should have 1 selected record");
        assert.containsOnce(target, '.o_documents_inspector_preview .o_document_preview',
            "should show 1 document preview in the DocumentsInspector");

        await toggleMenuItem(target, "OwO");

        assert.containsOnce(target, '.o_record_selected',
            "should have 1 selected records");
        assert.containsOnce(target, '.o_documents_inspector_preview .o_document_preview',
            "should show 1 document previews in the DocumentsInspector");
    });

    QUnit.test('selected records are kept when a button is clicked', async function (assert) {
        assert.expect(6);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                        <button name="some_method" type="object"/>
                    </div>
                </t></templates></kanban>`,
        });

        patchWithCleanup(kanban.env.services.action, {
            doActionButton(ev) {
                assert.strictEqual(ev.name, 'some_method',
                    "should call the correct method");
                pyEnv['documents.document'].write([ev.resId], { name: 'yop changed' });
                ev.onClose();
            },
        });

        kanban.model.root.records.filter(rec => ['yop', 'burp', 'blip'].includes(rec.data.name)).forEach(rec => rec.toggleSelection(true));
        await nextTick();

        assert.containsN(target, '.o_record_selected', 3,
            "should have 3 selected records");
        assert.containsN(target, '.o_documents_inspector_preview .o_document_preview', 3,
            "should show 3 document previews in the DocumentsInspector");

        await click(Array.from(target.querySelectorAll('.o_kanban_record button')).find(el => el.parentElement.textContent.trim() === "yop"));

        assert.strictEqual(Array.from(target.querySelectorAll('.o_record_selected')).filter(el => el.textContent.trim() === 'yop changed').length, 1,
            "should have re-rendered the updated record");
        assert.containsN(target, '.o_record_selected', 3,
            "should still have 3 selected records");
        assert.containsN(target, '.o_documents_inspector_preview .o_document_preview', 3,
            "should still show 3 document previews in the DocumentsInspector");
    });

    QUnit.test('can share current domain', async function (assert) {
        assert.expect(2);

        const [resUsersId1] = pyEnv['res.users'].search([['display_name', '=', 'Lukaku']]);
        const domain = ['owner_id', '=', resUsersId1];
        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            domain: [domain],
            mockRPC: async function (route, args) {
                if (args.method === 'open_share_popup') {
                    assert.deepEqual(args.args, [{
                        document_ids: false,
                        domain: [
                            "&",
                                domain,
                            "&",
                                ["folder_id", "child_of", 1],
                                ["res_model", "in", ["res.fake"]]
                        ],
                        folder_id: 1,
                        tag_ids: [[6, false, []]],
                        type: 'domain',
                    }]);
                    return { ignore: true };
                }
            },
        });

        const oldDoAction = kanban.env.services.action.doAction;
        patchWithCleanup(kanban.env.services.action, {
            doAction(action) {
                if (action.ignore) {
                    return;
                }
                return oldDoAction.call(this, action);
            },
        });
        await click(
            find(target, '.o_search_panel_category_value header', 1)
        );
        // filter on 'task' in the DocumentsSelector
        await click(
            find(target, '.o_search_panel_label_title', "Task")
        );

        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 1,
            "should have 2 records in the renderer");

        await click(target, '.o_documents_kanban_share_domain');
    });

    QUnit.test('can upload from URL', async function (assert) {
        assert.expect(1);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        patchWithCleanup(kanban.env.services.action, {
            doAction(action) {
                assert.deepEqual(action, 'documents.action_url_form', 'should open the url form');
            },
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('button.o_documents_kanban_url'));
    });

    QUnit.test('can Request a file', async function (assert) {
        assert.expect(1);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        patchWithCleanup(kanban.env.services.action, {
            doAction(action) {
                assert.deepEqual(action, 'documents.action_request_form', 'should open the url form');
            },
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('button.o_documents_kanban_request'));
    });

    QUnit.test("can navigate with arrows", async function (assert) {
        assert.expect(10);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban" class="o_documents_kanban_test"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });
        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(1) header'));
        // Force specific sizes for the test.
        // We will have rows of 2 cards each
        const kanbanEl = target.querySelector('.o_documents_kanban_test');
        kanbanEl.style.width = "500px";
        const cards = kanbanEl.querySelectorAll(".o_kanban_record");
        for (const card of cards) {
            card.style.width = "200px";
        }
        cards[0].focus();
        const triggerKey = async (key) => {
            await triggerEvent(document.activeElement, null, 'keydown', {
                key,
            })
        }
        await triggerKey('ArrowRight');
        assert.strictEqual(document.activeElement, cards[1], "should have moved to the next card");
        await triggerKey('ArrowDown');
        assert.strictEqual(document.activeElement, cards[3], "should have moved to card below");
        await triggerKey('ArrowLeft');
        assert.strictEqual(document.activeElement, cards[2], "should have moved to the card on the left");
        await triggerKey('ArrowLeft');
        assert.strictEqual(document.activeElement, cards[1], "should have moved to the last card of the previous row");
        await triggerKey('ArrowDown');
        assert.strictEqual(document.activeElement, cards[3], "should have moved to card below");
        await triggerKey('ArrowDown');
        assert.strictEqual(document.activeElement, cards[5], "should have moved to card below");
        await triggerKey('ArrowLeft');
        assert.strictEqual(document.activeElement, cards[4], "should have moved to the card on the left");
        await triggerKey('ArrowUp');
        assert.strictEqual(document.activeElement, cards[2], "should have moved one row up");
        await triggerKey('ArrowUp');
        assert.strictEqual(document.activeElement, cards[0], "should have moved one row up");
        await triggerKey('ArrowUp');
        assert.hasClass(document.activeElement, "o_searchview_input", "should have moved to the search input");
    });

    QUnit.module('DocumentsInspector');

    QUnit.test('document inspector with no document selected', async function (assert) {
        assert.expect(3);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        assert.strictEqual(target.querySelector('.o_documents_inspector_preview').textContent.replace(/\s+/g, ''),
            '_F1-test-description_', "should display the current workspace description");
        assert.strictEqual(target.querySelectorAll('.o_inspector_value')[0].textContent.trim(),
            '5', "should display the correct number of documents");
        assert.strictEqual(target.querySelectorAll('.o_inspector_value')[1].textContent.trim(),
            '0.12 MB', "should display the correct size");
    });

    QUnit.test('document inspector with selected documents', async function (assert) {
        assert.expect(5);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        // select a first document
        await click(target.querySelector('.o_kanban_record:nth-of-type(1) .o_record_selector'));

        assert.containsNone(target, '.o_documents_inspector_info .o_selection_size',
            "should not display the number of selected documents (because only 1)");
        assert.containsOnce(target, '.o_documents_inspector_preview .o_document_preview',
            "should show a preview of the selected document");
        assert.hasClass(target.querySelector('.o_documents_inspector_preview .o_document_preview'), 'o_documents_single_preview',
            "should have the 'o_documents_single_preview' className");

        // select a second document
        await click(target.querySelector('.o_kanban_record:nth-of-type(2) .o_record_selector'));

        assert.strictEqual(target.querySelector('.o_documents_inspector_preview .o_selection_size').textContent.trim(),
            '2 documents selected', "should display the correct number of selected documents");
        assert.containsN(target, '.o_documents_inspector_preview .o_document_preview', 2,
            "should show a preview of the selected documents");
    });

    QUnit.test('document inspector limits preview to 4 documents', async function (assert) {
        assert.expect(2);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        // select five documents
        for (let i = 0; i < 5; i++) {
            kanban.model.root.records[i].toggleSelection(true);
        }
        await nextTick();

        assert.strictEqual(target.querySelector('.o_documents_inspector_preview .o_selection_size').textContent.trim(),
            '5 documents selected', "should display the correct number of selected documents");
        assert.containsN(target, '.o_documents_inspector_preview .o_document_preview', 4,
            "should only show a preview of 4 selected documents");
    });

    QUnit.test('document inspector shows selected records of the current page', async function (assert) {
        assert.expect(6);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban" limit="2"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        kanban.model.root.records[0].toggleSelection(0);
        await nextTick();

        assert.containsOnce(target, '.o_record_selected',
            "should have 1 selected record");
        assert.containsOnce(target, '.o_documents_inspector_preview .o_document_preview',
            "should show 1 document preview in the DocumentsInspector");

        await pagerNext(target);

        assert.containsNone(target, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(target, '.o_documents_inspector_preview .o_document_preview',
            "should show no document preview in the DocumentsInspector");

        await pagerPrevious(target);

        assert.containsNone(target, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(target, '.o_documents_inspector_preview .o_document_preview',
            "should show no document preview in the DocumentsInspector");
    });

    QUnit.test('document inspector: document preview', async function (assert) {
        assert.expect(8);

        const views = {
            'documents.document,false,kanban': 
                `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                        </div>
                    </t></templates></kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        assert.containsNone(target, '.o_document_preview img',
            "should not have a clickable image");

        await click(find(target, '.o_kanban_record', 'burp'));

        assert.containsNone(target, '.o_AttachmentViewer',
            "should not have a document preview");
        assert.containsOnce(target, '.o_document_preview img',
            "should have a clickable image");

        await click(target, '.o_document_preview img');

        assert.containsOnce(target, '.o_AttachmentViewer',
            "should have a document preview");
        assert.containsOnce(target, '.o_AttachmentViewer_headerItemButtonClose',
            "should have a close button");

        await click(target, '.o_AttachmentViewer_headerItemButtonClose');

        await click(find(target, '.o_kanban_record', 'blip'));

        await click(target, '.o_preview_available');

        assert.containsOnce(target, '.o_AttachmentViewer_buttonSplit', "should have a pdf splitter");
        assert.containsOnce(target, 'iframe[data-src="/web/static/lib/pdfjs/web/viewer.html?file=/web/content/2?model=documents.document"]',
            "should have an iframe with the correct pdfviewer src");

        await click(target, '.o_AttachmentViewer_headerItemButtonClose');

        assert.containsNone(target, '.o_AttachmentViewer',
            "should not have a document preview after pdf exit");
    });

    QUnit.test('document inspector: open preview while modifying document', async function (assert) {
        assert.expect(2);
        var def = testUtils.makeTestPromise();

        const views = {
            'documents.document,false,kanban': 
                `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                        <div>
                            <field name="name"/>
                        </div>
                    </t></templates></kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
            mockRPC: async (route, args) => {
                if (args.method === 'write') {
                    return def;
                }
            },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'burp'));

        await editInput(target, 'div[name=name] input', 'foo');

        await click(target, '.o_document_preview img');
        await nextTick();
        assert.containsNone(target, '.o_AttachmentViewer',
            "document preview should have been canceled");

        def.resolve();
        await nextTick();
        await click(target, '.o_document_preview img');
        await nextTick();
        assert.containsOnce(target, '.o_AttachmentViewer',
                "should have a document preview");
        await click(target, '.o_AttachmentViewer_headerItemButtonClose');
    });

    QUnit.test('document inspector: can delete records', async function (assert) {
        assert.expect(5);

        const selectedRecordIds = pyEnv['documents.document'].search(['&', ['name', 'in', ['wip', 'zorro']], ['active', '=', false]]);
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            domain: [['active', '=', false]],
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (args.method === 'unlink') {
                    assert.deepEqual(args.args[0], selectedRecordIds,
                        "should unlink the selected records");
                }
            },
        });

        await click(find(target, '.o_kanban_record', 'wip'), '.o_record_selector');
        await click(find(target, '.o_kanban_record', 'zorro'), '.o_record_selector');

        assert.containsN(target, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsN(target, '.o_documents_inspector_preview .o_document_preview', 2,
            "should show 2 document previews in the DocumentsInspector");

        await click(target.querySelector('.o_documents_inspector_info .o_inspector_delete'));
        // await nextTick();

        assert.containsNone(target, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(target, '.o_documents_inspector_preview .o_document_preview',
            "should show 0 document preview in the DocumentsInspector");
    });

    QUnit.test('document inspector: can archive records', async function (assert) {
        assert.expect(5);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(find(target, '.o_kanban_record', 'yop'), '.o_record_selector');
        await click(find(target, '.o_kanban_record', 'burp'), '.o_record_selector');

        assert.containsN(target, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsN(target, '.o_documents_inspector_preview .o_document_preview', 2,
            "should show 2 document previews in the DocumentsInspector");

        await click(target.querySelector('.o_documents_inspector_info .o_inspector_archive'));

        assert.containsNone(target, '.o_record_selected',
            "should have no selected record");
        assert.containsNone(target, '.o_documents_inspector_preview .o_document_preview',
            "should show no document preview in the DocumentsInspector");

        await kanban.model.root.load();

        assert.containsNone(target, '.o_kanban_renderer .o_record_selected',
            "should have no selected archived record");
    });

    QUnit.test('document inspector: can share records', async function (assert) {
        assert.expect(3);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async (route, args) => {
                if (args.method === 'action_get_share_url') {
                    assert.deepEqual(args.args, [{
                        document_ids: [[6, false, [1, 2]]],
                        folder_id: 1,
                        type: 'ids',
                    }]);
                    return "localhost/share";
                }
            },
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(find(target, '.o_kanban_record', 'yop'), '.o_record_selector');
        await click(find(target, '.o_kanban_record', 'blip'), '.o_record_selector');

        assert.containsN(target, '.o_record_selected', 2,
            "should have 2 selected records");

        await click(target.querySelector('.o_documents_inspector_info .o_inspector_share'));
        assert.containsN(target, ".o_notification_body", 1, "should have a notification");
    });

    QUnit.test('document inspector: locked records', async function (assert) {
        assert.expect(6);

        pyEnv.currentUserId = pyEnv['res.users'].search([['display_name', '=', 'Hazard']])[0];
        patchWithCleanup(session, { uid: pyEnv.currentUserId });
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        // select a record that is locked by ourself
        await click(find(target, '.o_kanban_record', 'zip'));

        assert.hasClass(target.querySelector('.o_inspector_lock'), 'o_locked',
            "this attachment should be locked");
        assert.notOk(target.querySelector('.o_inspector_lock').disabled,
            "lock button should not be disabled");
        assert.notOk(target.querySelector('.o_inspector_replace').disabled,
            "replace button should not be disabled");

        // select a record that is locked by someone else
        await click(find(target, '.o_kanban_record', 'gnap'));

        assert.hasClass(target.querySelector('.o_inspector_lock'), 'o_locked',
            "this attachment should be locked as well");
        assert.ok(target.querySelector('.o_inspector_replace').disabled,
            "replace button should be disabled");
        assert.ok(target.querySelector('.o_inspector_archive').disabled,
            "archive button should be disabled");
    });

    QUnit.test('document inspector: can (un)lock records', async function (assert) {
        assert.expect(5);

        pyEnv.currentUserId = pyEnv['res.users'].search([['display_name', '=', 'Hazard']])[0];
        patchWithCleanup(session, { uid: pyEnv.currentUserId });
        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async (route, args, performRpc) => {
                if (route === '/web/dataset/call_kw/documents.document/toggle_lock') {
                    assert.deepEqual(args.args, [1], "should call method for the correct record");
                    const record = kanban.model.root.records.find(rec => rec.resId === 1);
                    return performRpc('', {
                        method: 'write',
                        model: 'documents.document',
                        args: [
                            [1],
                            { lock_uid: record.data.lock_uid ? false : pyEnv.currentUserId },
                        ],
                    });
                }
            },
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        assert.doesNotHaveClass(target.querySelector('.o_inspector_lock'), 'o_locked',
            "this attachment should not be locked");

        // lock the record
        await click(target.querySelector('.o_inspector_lock'));

        assert.hasClass(target.querySelector('.o_inspector_lock'), 'o_locked',
            "this attachment should be locked");

        // unlock the record
        await click(target.querySelector('.o_inspector_lock'));

        assert.doesNotHaveClass(target.querySelector('.o_inspector_lock'), 'o_locked',
            "this attachment should not be locked anymore");
    });

    QUnit.test('document inspector: document info with one document selected', async function (assert) {
        assert.expect(6);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        assert.strictEqual(target.querySelector('.o_field_widget[name=name] input').value,
            'yop', "should correctly display the name");
        assert.strictEqual(target.querySelector('.o_field_widget[name=owner_id] input').value,
            'Hazard', "should correctly display the owner");
        assert.strictEqual(target.querySelector('.o_field_widget[name=partner_id] input').value,
            'Lukaku', "should correctly display the related partner");
        assert.containsNone(target, '.o_field_many2one .o_external_button:visible',
            "should not display the external button in many2ones");
        assert.strictEqual(target.querySelector('.o_inspector_model_name').textContent,
            ' Task', "should correctly display the resource model");
        assert.strictEqual(target.querySelector('.o_inspector_object_name').textContent,
            'Write specs', "should correctly display the resource name");
    });

    QUnit.test('document inspector: update document info with one document selected', async function (assert) {
        assert.expect(7);
        let count = 0;

        const [deBruyneUserId] = pyEnv['res.users'].search([['display_name', '=', 'De Bruyne']]);
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                        <field name="owner_id"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async function (route, args) {
                if (args.method === 'write') {
                    count++;
                    switch (count) {
                        case 1:
                            assert.deepEqual(args.args, [[1], {owner_id: deBruyneUserId }],
                                "should save the change directly");
                            break;
                        case 2:
                            assert.deepEqual(args.args, [[1], {owner_id: false}],
                                "should save false value");
                            break;
                    }
                }
            },
        });

        const firstRecord = find(target, '.o_kanban_record', 'yopHazard');
        assert.strictEqual(firstRecord.textContent, 'yopHazard',
            "should display the correct owner");

        await click(firstRecord);

        assert.hasClass(firstRecord, 'o_record_selected');

        // change m2o value
        const input = await clickOpenM2ODropdown(target, "owner_id");
        await editInput(input, null, "De Bruyne");
        await clickOpenedDropdownItem(target, "owner_id", "De Bruyne");

        assert.strictEqual(firstRecord.textContent, 'yopDe Bruyne',
            "should have updated the owner");
        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should still be selected");
        assert.strictEqual(target.querySelector('.o_field_many2one[name=owner_id] input').value, 'De Bruyne',
            "should display the new value in the many2one");

        await editInput(input, null, "");
    });

    QUnit.test('document inspector: document info with several documents selected', async function (assert) {
        assert.expect(7);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        // select two records with same m2o value
        const blip = find(target, '.o_kanban_record', 'blip');
        const gnap = find(target, '.o_kanban_record', 'gnap');
        await click(blip);
        await click(gnap, '.o_record_selector');

        assert.hasClass(blip, 'o_record_selected',
            "blip record should be selected");
        assert.hasClass(gnap, 'o_record_selected',
            "gnap record should be selected");

        assert.strictEqual(target.querySelector('.o_field_many2one[name=owner_id] span').textContent,
            'Lukaku', "should display the correct m2o value");
        assert.containsNone(target, '.o_field_many2one .o_external_button:visible',
            "should not display the external button in many2one");

        // select a third record with another m2o value
        const yop = find(target, '.o_kanban_record', 'yop');
        await click(yop, '.o_record_selector');
        assert.hasClass(yop, 'o_record_selected',
            "yop record should be selected");

        assert.strictEqual(target.querySelector('.o_field_many2one[name=owner_id] span').textContent,
            'Multiple values', "should display 'Multiple values'");
        assert.containsNone(target, '.o_field_many2one .o_external_button:visible',
            "should not display the external button in many2one");
    });

    QUnit.test('document inspector: update document info with several documents selected', async function (assert) {
        assert.expect(10);

        const [deBruyneUserId] = pyEnv['res.users'].search([['display_name', '=', 'De Bruyne']]);
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                        <field name="owner_id"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args, [[1, 2], {owner_id: deBruyneUserId}],
                        "should save the change directly");
                }
            },
        });

        const firstRecord = target.querySelector('.o_kanban_record');
        assert.strictEqual(firstRecord.textContent, 'yopHazard',
            "should display the correct owner (record 1)");
        const secondRecord = target.querySelector('.o_kanban_record:nth-of-type(2)');
        assert.strictEqual(secondRecord.textContent, 'blipLukaku',
            "should display the correct owner (record 2)");

        await click(firstRecord);
        await click(secondRecord, '.o_record_selector');

        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should be selected");
        assert.hasClass(secondRecord, 'o_record_selected',
            "second record should be selected");

        // change m2o value
        const input = await clickOpenM2ODropdown(target, "owner_id");
        await editInput(input, null, "De Bruyne");
        await clickOpenedDropdownItem(target, "owner_id", "De Bruyne");

        assert.strictEqual(firstRecord.textContent, 'yopDe Bruyne',
            "should have updated the owner of first record");
        assert.strictEqual(secondRecord.textContent, 'blipDe Bruyne',
            "should have updated the owner of second record");
        assert.hasClass(firstRecord, 'o_record_selected',
            "first record should still be selected");
        assert.hasClass(secondRecord, 'o_record_selected',
            "second record should still be selected");
        assert.strictEqual(target.querySelector('.o_field_many2one[name=owner_id] input').value, 'De Bruyne',
            "should display the new value in the many2one");
    });

    QUnit.test('document inspector: update info: handle concurrent updates', async function (assert) {
        assert.expect(11);

        const def = testUtils.makeTestPromise();
        let nbWrite = 0;
        let value;
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async function (route, args, performRpc) {
                if (args.method === 'write') {
                    const result = performRpc(route, args);
                    assert.step('write');
                    nbWrite++;
                    assert.deepEqual(args.args, [[1], {name: value}],
                        "should correctly save the changes");
                    if (nbWrite === 1) {
                        return def.then(() => result);
                    }
                    return result;
                }
            },
        });

        assert.strictEqual(target.querySelector('.o_kanban_record').textContent, 'yop',
            "should display the correct filename");
        await click(target.querySelector('.o_kanban_record'));

        // change filename value of selected record (but block RPC)
        value = 'temp name';
        await editInput(target.querySelector('div[name=name] input'), null, value);

        assert.strictEqual(target.querySelector('.o_kanban_record').textContent, 'yop',
            "should still display the old filename");

        // change filename value again (this RPC isn't blocked but must wait for
        // the first one to return)
        value = 'new name';
        await editInput(target.querySelector('div[name=name] input'), null, value);

        assert.strictEqual(target.querySelector('.o_kanban_record').textContent, 'yop',
            "should still display the old filename");

        assert.step('resolve');
        def.resolve();
        await nextTick();

        assert.strictEqual(target.querySelector('.o_kanban_record').textContent, 'new name',
            "should still display the new filename in the record");
        assert.strictEqual(target.querySelector('.o_field_char[name=name] input').value, 'new name',
            "should still display the new filename in the document inspector");

        assert.verifySteps(['write', 'resolve', 'write']);
    });

    QUnit.test('document inspector: open resource', async function (assert) {
        assert.expect(2);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            async mockRPC(route, args) {
                if (args.method === 'get_formview_action') {
                    assert.strictEqual(args.model, 'res.fake',
                        "should fetch the action for res.fake")
                    return { ignore: true };
                }
            },
        });

        patchWithCleanup(kanban.env.services.action, {
            doAction(action) {
                assert.ok(action.ignore, "should call the action after loading it");
            },
        });

        await click(target.querySelector('.o_kanban_record'));

        await click(target.querySelector('.o_documents_inspector .o_inspector_object_name'));
    });

    QUnit.test('document inspector: display tags of selected documents', async function (assert) {
        assert.expect(4);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));

        assert.containsN(target, '.o_inspector_tag', 2,
            "should display the tags of the selected document");

        await click(target.querySelector('.o_kanban_record:nth-of-type(2) .o_record_selector'));

        assert.containsN(target, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsOnce(target, '.o_inspector_tag',
            "should display the common tags between the two selected documents");
        assert.strictEqual(target.querySelector('.o_inspector_tag').textContent.replace(/\s/g, ""), 'Status>Draft×',
            "should correctly display the content of the tag");
    });

    QUnit.test('document inspector: input to add tags is hidden if no tag to add', async function (assert) {
        assert.expect(2);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(find(target, '.o_kanban_record', 'gnap'));

        assert.containsN(target, '.o_inspector_tag', 3,
            "should have 3 tags");
        assert.containsNone(target, '.o_inspector_tags .o_inspector_tag_add',
            "should not have an input to add tags");
    });

    QUnit.test('document inspector: remove tag', async function (assert) {
        assert.expect(4);

        pyEnv.currentUserId = pyEnv['res.users'].search([['display_name', '=', 'Hazard']])[0];
        patchWithCleanup(session, { uid: pyEnv.currentUserId });
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[0], [1, 5],
                        "should write on the selected records");
                    assert.deepEqual(args.args[1], {
                        tag_ids: [[3, 2, false]],
                    }, "should write the correct value");
                }
            },
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));
        await click(target.querySelector('.o_kanban_record:nth-of-type(5) .o_record_selector'));

        assert.containsN(target, '.o_inspector_tag', 2,
            "should display two tags");

        await click(target.querySelector('.o_inspector_tag:nth-of-type(2) .o_inspector_tag_remove'));

        assert.containsOnce(target, '.o_inspector_tag',
            "should display one tag");
    });

    QUnit.test('document inspector: add a tag', async function (assert) {
        assert.expect(8);

        // Make autocomplete input instantaneous
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        const [lastDocumentsTagId] = pyEnv['documents.tag'].search([['display_name', '=', 'No stress']]);
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[0], [1, 2],
                        "should write on the selected records");
                    assert.deepEqual(args.args[1], {
                        tag_ids: [[4, lastDocumentsTagId, false]],
                    }, "should write the correct value");
                }
            },
        });


        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));
        await click(target.querySelector('.o_kanban_record:nth-of-type(2) .o_record_selector'));
        
        const input = target.querySelector('.o_inspector_tags input');

        assert.notOk(input === document.activeElement,
            "the tag input should not be focused");

        await click(input);
        assert.containsOnce(target, '.o_inspector_tag');

        let autocompleteValues = target.querySelectorAll('.o_inspector_tags ul li');
        assert.strictEqual(autocompleteValues.length, 2,
            "Should have 2 entries in the autocomplete dropdown");

        await editInput(input, null, 'stress');
        autocompleteValues = target.querySelectorAll('.o_inspector_tags ul li');
        assert.strictEqual(autocompleteValues.length, 1,
            "Should only have one entry in the autocomplete dropdown");
        await click(target.querySelector('.o_inspector_tags ul li'));

        assert.containsN(target, '.o_inspector_tag', 2,
            "should display two tags");
        assert.strictEqual(input, document.activeElement,
            "the tag input should be focused");
    });

    QUnit.test('document inspector: do not suggest already linked tags', async function (assert) {
        assert.expect(2);

        // Make autocomplete input instantaneous
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));

        assert.containsN(target, '.o_inspector_tag', 2,
            "should display two tags");

        await click(target.querySelector('.o_inspector_tags input'));
        await editInput(target.querySelector('.o_inspector_tags input'), null, 'new');
        assert.strictEqual(target.querySelectorAll('.o_inspector_tags ul li').length, 0,
            "should have no entry in the autocomplete drodown");
    });

    QUnit.test('document inspector: tags: trigger a search on input clicked', async function (assert) {
        assert.expect(1);

        // Make autocomplete input instantaneous
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));

        await click(target.querySelector('.o_inspector_tags input'));
        assert.strictEqual(target.querySelectorAll('.o_inspector_tags ul li').length, 1,
            "should have no entry in the autocomplete drodown");
    });

    QUnit.test('document inspector: unknown tags are hidden', async function (assert) {
        assert.expect(1);

        const [firstDocumentRecord] = pyEnv['documents.document'].searchRead([]);
        pyEnv['documents.document'].write([firstDocumentRecord.id], { tag_ids: [...firstDocumentRecord.tag_ids, 42] });
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));

        assert.containsN(target, '.o_inspector_tag', 2,
            "should not display the unknown tag");
    });

    QUnit.test('document inspector: display rules of selected documents', async function (assert) {
        assert.expect(6);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));

        assert.containsN(target, '.o_inspector_rule', 3,
            "should display the rules of the selected document");

        await click(target.querySelector('.o_kanban_record:nth-of-type(2)'), '.o_record_selector');

        assert.containsN(target, '.o_record_selected', 2,
            "should have 2 selected records");
        assert.containsOnce(target, '.o_inspector_rule',
            "should display the common rules between the two selected documents");
        assert.containsOnce(target, '.o_inspector_rule .o_inspector_trigger_rule',
            "should display the button for the common rule");
        assert.strictEqual(target.querySelector('.o_inspector_rule').textContent.trim(), 'Convincing AI not to turn evil',
            "should correctly display the content of the rule");
        assert.hasAttrValue(target.querySelector('.o_inspector_rule span'), 'title', "Racing for AI Supremacy",
            "should correctly display the tooltip of the rule");
    });

    QUnit.test('document inspector: displays the right amount of single record rules', async function (assert) {
        assert.expect(2);

        pyEnv.currentUserId = pyEnv['res.users'].search([['display_name', '=', 'Hazard']])[0];
        patchWithCleanup(session, { uid: pyEnv.currentUserId });
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));

        assert.containsN(target, '.o_inspector_rule', 3,
            "should display the rules of the selected document (2 multi record, 1 single record)");

        await click(target.querySelectorAll('.o_kanban_record')[4], '.o_record_selector');

        assert.containsN(target, '.o_inspector_rule', 2,
            "should display the rules in common except the single record rule");
    });

    QUnit.test('document inspector: locked by another user', async function (assert) {
        assert.expect(4);

        const resUsersId1 = pyEnv['res.users'].create({});
        pyEnv['documents.document'].create({
            folder_id: pyEnv['documents.folder'].search([])[0],
            lock_uid: resUsersId1,
            name: 'lockedByAnother',
        });
        pyEnv.currentUserId = pyEnv['res.users'].search([['display_name', '=', 'Lukaku']])[0];
        patchWithCleanup(session, { uid: pyEnv.currentUserId });
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(find(target, '.o_kanban_record', 'lockedByAnother'));

        assert.containsNone(target, '.o_inspector_rule', "should not display any rule");

        assert.ok(target.querySelector('.o_inspector_lock').disabled, "the lock button should be disabled");
        assert.ok(target.querySelector('.o_inspector_replace').disabled, "the replace button should be disabled");
        assert.ok(target.querySelector('.o_inspector_archive').disabled, "the archive button should be disabled");
    });

    QUnit.test('document inspector: display rules of reloaded record', async function (assert) {
        assert.expect(9);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                        <button name="some_method" type="object"/>
                    </div>
                </t></templates></kanban>`,
        });

        patchWithCleanup(kanban.env.services.action, {
            doActionButton(action) {
                assert.strictEqual(action.name, 'some_method',
                    "should call the correct method");
                kanban.orm.write(
                    'documents.document',
                    [action.resId],
                    { name: 'yop changed' },
                    kanban.context,
                );
                action.onClose();
            },
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(find(target, '.o_kanban_record', 'yop'));

        assert.containsN(target, '.o_inspector_rule span', 3,
            "should display the rules of the selected document");

        assert.strictEqual(target.querySelector('.o_inspector_rule:nth-of-type(1) span').textContent, 'Convincing AI not to turn evil',
            "should display the right rule");

        assert.strictEqual(target.querySelector('.o_inspector_rule:nth-of-type(2) span').textContent, 'Follow the white rabbit',
            "should display the right rule");

        assert.strictEqual(target.querySelector('.o_inspector_rule:nth-of-type(3) span').textContent, 'One record rule',
            "should display the right rule");

        // click on the button to reload the record
        await click(find(target, '.o_kanban_record', 'yop'), 'button');

        assert.strictEqual($(target).find('.o_record_selected:contains(yop changed)').length, 1,
            "should have reloaded the updated record");

        assert.strictEqual(target.querySelector('.o_inspector_rule:nth-of-type(1) span').textContent, 'Convincing AI not to turn evil',
            "should display the right rule");

        assert.strictEqual(target.querySelector('.o_inspector_rule:nth-of-type(2) span').textContent, 'Follow the white rabbit',
            "should display the right rule");

        assert.strictEqual(target.querySelector('.o_inspector_rule:nth-of-type(3) span').textContent, 'One record rule',
            "should display the right rule");
    });

    QUnit.test('document inspector: trigger rule actions on selected documents', async function (assert) {
        assert.expect(3);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async function (route, args) {
                if (args.model === 'documents.workflow.rule' && args.method === 'apply_actions') {
                    assert.deepEqual(args.args[0], [1],
                        "should execute actions on clicked rule");
                    assert.deepEqual(args.args[1], [1, 2],
                        "should execute actions on the selected records");
                    return Promise.resolve(true);
                }
            },
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));
        await click(target.querySelector('.o_kanban_record:nth-of-type(2) .o_record_selector'));

        assert.containsOnce(target, '.o_inspector_rule',
            "should display the common rules between the two selected documents");
        await click(target.querySelector('.o_inspector_rule .o_inspector_trigger_rule'));
    });

    QUnit.test('document inspector: checks the buttons deleting/editing a link between a document and a record', async function (assert) {
        assert.expect(6);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                        <field name="is_editable_attachment" invisible="1"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async function (route, args, performRPC) {
                if (args.method === 'check_access_rights') {
                    return true;
                } else if (args.model === 'documents.workflow.rule' && args.method === 'unlink_record') {
                    performRPC(
                        '',
                        {
                            model: 'documents.document',
                            method: 'write',
                            args: [
                                args.args[0],
                                {
                                    res_model: 'documents.document',
                                    res_id: false,
                                    is_editable_attachment: false,
                                },
                            ],
                        },
                    );
                    return true;
                }
            },
        });

        // Document with an editable link.
        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        await click(target.querySelector('.o_kanban_record'));

        assert.containsOnce(target, '.o_inspector_model_button.o_inspector_model_edit',
            "should display the edit button of the link between the document and the record on the inspector.");
        assert.containsOnce(target, '.o_inspector_model_button.o_inspector_model_delete',
            "should display the delete button of the link between the document and the record on the inspector.");

        // Delete the link
        await click(target.querySelector('.o_inspector_model_delete'));
        await click(target.querySelector('.modal-footer .btn-primary'));
        assert.containsNone(target, 'o_inspector_custom_field .o_model_container',
            "should display no records link to the document");

        // Document with a non-editable link
        await click(target.querySelector('.o_kanban_record'));
        await click(target.querySelector('.o_kanban_record:nth-of-type(2) .o_record_selector'));

        assert.containsNone(target, 'o_inspector_custom_field .o_model_container',
            "should display a record link to the document");
        assert.containsNone(target, '.o_inspector_model_button.o_inspector_model_edit',
            "should not display the edit button of the link between the document and the record on the inspector.");
        assert.containsNone(target, '.o_inspector_model_button.o_inspector_model_delete',
            "should not display the delete button of the link between the document and the record on the inspector.");
    });

    QUnit.test('document inspector: quick create not enabled in dropdown', async function (assert) {
        assert.expect(2);

       await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });
        await click(target.querySelector('.o_kanban_record'));
        const input = await clickOpenM2ODropdown(target, 'partner_id');
        await editInput(input, null, "Dupont");
        assert.strictEqual(target.querySelectorAll('.ui-autocomplete .o_m2o_dropdown_option').length, 1,
            "Dropdown should be opened and have only one item");
        assert.notEqual(
            target.querySelector('.ui-autocomplete .o_m2o_dropdown_option').textContent,
            'Create "Dupont"',
            'there should not be a quick create in dropdown'
        );
    });

    QUnit.module('DocumentChatter');

    QUnit.test('document chatter: open and close chatter', async function (assert) {
        assert.expect(7);

        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        assert.containsNone(document.body, '.o_Chatter',
            "should not display any chatter");

        // select a record
        await click(find(target, '.o_kanban_record', 'yop'));

        assert.containsNone(document.body, '.o_Chatter',
            "should still not display any chatter");

        // open the chatter
        await click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(target, '.o_Chatter',
            "should display the chatter");
        assert.containsOnce(target, '.o_search_panel:visible',
            "documents selector should still be visible");
        assert.containsOnce(target, '.o_kanban_renderer:visible',
            "kanban view should still be visible");
        assert.containsOnce(target, '.o_documents_inspector:visible',
            "document inspector should still be visible");

        // close the chatter
        await click(target.querySelector('.o_ChatterTopbar_buttonClose'));
        assert.containsNone(target, '.o_document_chatter_container .o_Chatter',
            "should no longer display the chatter");
    });

    QUnit.test('document chatter: fetch and display chatter messages', async function (assert) {
        assert.expect(2);

        const [documentsDocumentId1] = pyEnv['documents.document'].search([]);
        pyEnv['mail.message'].create([
            { body: "Message 2", model: 'documents.document', res_id: documentsDocumentId1 },
            { body: "Message 1", model: 'documents.document', res_id: documentsDocumentId1 },
        ]);

        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await afterNextRender(() =>
            click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'))
        );
        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsN(target, '.o_document_chatter_container .o_Chatter .o_Message', 2,
            "should display two messages in the chatter");
    });

    QUnit.test('document chatter: fetch and display followers', async function (assert) {
        assert.expect(3);

        const [documentsDocumentId1] = pyEnv['documents.document'].search([]);
        const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].search([]);
        pyEnv['mail.followers'].create([
            {
                email: 'raoul@grosbedon.fr',
                name: 'Raoul Grosbedon',
                partner_id: resPartnerId1,
                res_id: documentsDocumentId1,
                res_model: 'documents.document',
            },
            {
                email: 'raoulette@grosbedon.fr',
                name: 'Raoulette Grosbedon',
                partner_id: resPartnerId2,
                res_id: documentsDocumentId1,
                res_model: 'documents.document',
            },
        ]);
        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(
            target,
            '.o_document_chatter_container .o_Chatter',
            "should display the chatter"
        );
        assert.containsOnce(target,
            '.o_document_chatter_container .o_FollowerListMenu',
            "should display the follower widget"
        );
        assert.strictEqual(
            target.querySelector('.o_FollowerListMenu_buttonFollowersCount').textContent,
            "2",
            "should have two followers"
        );
    });

    QUnit.test('document chatter: render the activity button', async function (assert) {
        assert.expect(3);

        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { env, openView } = await createDocumentsViewWithMessaging({
            hasWebClient: true,
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });
        patchWithCleanup(env.services.action, {
            doAction(action) {
                assert.deepEqual(action, {
                    context: {
                        default_res_id: 1,
                        default_res_model: 'documents.document'
                    },
                    name: "Schedule Activity",
                    res_id: false,
                    res_model: 'mail.activity',
                    target: 'new',
                    type: 'ir.actions.act_window',
                    view_mode: 'form',
                    views: [[false, 'form']]
                    },
                    "the activity button should trigger do_action with the correct args"
                );
            },
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        const activityButtons = target.querySelectorAll('.o_document_chatter_container .o_ChatterTopbar_buttonScheduleActivity');
        assert.strictEqual(activityButtons.length, 1,
            "should display the activity button");
        await click(activityButtons[0]);
    });

    QUnit.test('document chatter: render the activity button 2', async function (assert) {
        assert.expect(8);

        pyEnv['mail.activity'].create({
            can_write: true,
            create_uid: pyEnv.currentUserId,
            date_deadline: moment().format("YYYY-MM-DD"),
            display_name: "An activity",
            res_id: pyEnv['documents.document'].search([])[0],
            res_model: 'documents.document',
            state: "today",
            user_id: pyEnv.currentUserId,
        });

        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        assert.containsOnce(target, '.o_ActivityBox',
            "should display the activity area");
        assert.containsOnce(target, '.o_Activity',
            "should display an activity");
        assert.strictEqual(target.querySelectorAll('.o_Activity_markDoneButton').length, 1,
            "should display the activity mark done button");
        assert.containsOnce(target, '.o_Activity_editButton',
            "should display the activity Edit button");
        assert.containsOnce(target, '.o_Activity_cancelButton',
            "should display the activity Cancel button");
        
        await click(find(target, '.o_kanban_record', 'blip'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsNone(target, '.o_Activity',
            "should not display an activity");
    });

    QUnit.test('document chatter: can write messages in the chatter', async function (assert) {
        assert.expect(7);

        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            async mockRPC(route, args) {
                if (route === '/mail/get_suggested_recipients') {
                    return { 1: [] };
                }
                if (route === '/mail/message/post') {
                    assert.deepEqual(args.thread_id, 1,
                        "should post message on correct record");
                    assert.strictEqual(args.post_data.body, 'Some message',
                        "should post correct message");
                }
            },
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsNone(target, '.o_document_chatter_container .o_Composer',
            "chatter composer should not be open");

        // open the composer
        await click(target.querySelector('.o_document_chatter_container .o_ChatterTopbar_buttonSendMessage'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Composer',
            "chatter composer should be open");

        // write and send a message (need to wait the Send button to be enabled)
        target.querySelector(`.o_ComposerTextInput_textarea`).focus();
        await afterNextRender(() => {
            document.execCommand('insertText', false, "Some message");
        });
        await click(target.querySelector('.o_Composer_buttonSend'));
        assert.containsOnce(target, '.o_Message',
            "a message should have been created"
        );
        assert.strictEqual(
            target.querySelector('.o_Message_content').textContent,
            "Some message",
            "the created message should have the right body"
        );
    });

    QUnit.test('document chatter: keep chatter open when switching between records', async function (assert) {
        assert.expect(6);

        const [documentsDocumentId1, documentsDocumentId2] = pyEnv['documents.document'].search([]);
        pyEnv['mail.message'].create([
            { body: "Message on 'yop'", model: 'documents.document', res_id: documentsDocumentId1 },
            { body: "Message on 'blip'", model: 'documents.document', res_id: documentsDocumentId2 }
        ]);

        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await afterNextRender(() =>
            click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'))
        );
        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");
        assert.containsOnce(target, '.o_document_chatter_container .o_Message',
            "should display one message in the chatter");
        assert.strictEqual(target.querySelector('.o_Message .o_Message_content').innerText.trim(),
            "Message on 'yop'", "should display the correct message");

        // select another record
        await click(find(target, '.o_kanban_record', 'blip'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should still display the chatter");
        assert.containsOnce(target, '.o_document_chatter_container .o_Message',
            "should display one message in the chatter");
        assert.strictEqual(target.querySelector('.o_Message .o_Message_content').innerText.trim(),
            "Message on 'blip'", "should display the correct message");
    });

    QUnit.test('document chatter: keep chatter open after a reload', async function (assert) {
        assert.expect(3);

        const views = {
            'documents.document,false,kanban':
                `<kanban js_class="documents_kanban">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <i class="fa fa-circle-thin o_record_selector"/>
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            'documents.document,false,search':
                `<search>
                    <filter name="owo" string="OwO" domain="[['id', '&lt;', 4]]"/>
                </search>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        // reload with a domain
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "OwO");

        assert.containsOnce(target, '.o_record_selected',
            "record should still be selected");
        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should still display the chatter");
    });

    QUnit.test('document chatter: close chatter when more than one record selected', async function (assert) {
        assert.expect(2);

        const views = {
            'documents.document,false,kanban':
            `<kanban js_class="documents_kanban">
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <i class="fa fa-circle-thin o_record_selector"/>
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await click(target.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(target, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        await click(find(target, '.o_kanban_record', 'blip'), '.o_record_selector');

        assert.containsNone(target, '.o_document_chatter_container .o_Chatter',
            "should have closed the chatter");
    });

    QUnit.test('document chatter: close chatter when no more selected record', async function (assert) {
        assert.expect(3);

        const views = {
            'documents.document,false,kanban':
            `<kanban js_class="documents_kanban">
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <i class="fa fa-circle-thin o_record_selector"/>
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        'documents.document,false,search':
            `<search>
                <filter name="owo" string="OwO" domain="[['id', '&gt;', 4]]"/>
            </search>`,
        };
        const { openView } = await createDocumentsViewWithMessaging({
            serverData: { views },
        });
        await openView({
            res_model: 'documents.document',
            views: [[false, 'kanban']],
        });

        await click(find(target, '.o_kanban_record', 'yop'));

        await click(document.querySelector('.o_documents_inspector .o_inspector_open_chatter'));

        assert.containsOnce(document.body, '.o_document_chatter_container .o_Chatter',
            "should display the chatter");

        // reload with a domain
        await toggleFilterMenu(document);
        await toggleMenuItem(document, "OwO");

        assert.containsNone(document.body, '.o_record_selected',
            "no more record should be selected");
        assert.containsNone(document.body, '.o_document_chatter_container .o_Chatter',
            "should have closed the chatter");
    });

    QUnit.module('DocumentsSelector');

    QUnit.test('document selector: basic rendering', async function (assert) {
        assert.expect(18);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        assert.strictEqual(target.querySelectorAll('.o_search_panel .o_search_panel_section .o_search_panel_section_header')[0].textContent.trim(),
            'Workspace', "should have a 'Workspace' section");
        assert.containsN(target, '.o_search_panel .o_search_panel_category_value', 3,
            "three of them should be visible");
        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        assert.strictEqual(target.querySelector('.o_documents_inspector_preview').textContent.replace(/\s+/g, ''),
            '_F1-test-description_', "should display the first workspace");

        assert.strictEqual(target.querySelectorAll('.o_search_panel .o_search_panel_section .o_search_panel_section_header')[1].textContent.trim(),
            'Tags', "should have a 'tags' section");
        assert.containsN(target, '.o_search_panel .o_search_panel_filter_group', 2,
            "should have 2 facets");

        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:nth-of-type(1) label:nth-of-type(1) > span').textContent.replace(/\s/g, ''),
            '●Priority', "the first facet should be 'Priority'");
        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:nth-of-type(1) label:nth-of-type(1)').title.trim(),
            'A priority tooltip', "the first facet have a tooltip");
        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:last-child label:nth-of-type(1) > span').textContent.replace(/\s/g, ''),
            '●Status', "the last facet should be 'Status'");
        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:last-child label:nth-of-type(1)').title.trim(),
            'A Status tooltip', "the last facet should be 'Status'");

        assert.containsN(target, '.o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value', 2,
            "should have 2 tags in the last facet");

        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:nth-of-type(1) label').textContent.trim(),
            'Draft', "the first tag in the last facet should be 'Draft'");
        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:nth-of-type(1) label').title.trim(),
            'A Status tooltip', "the first tag in the last facet have a tooltip");
        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:last-child label').textContent.trim(),
            'New', "the last tag in the last facet should be 'New'");
        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_filter_group:last-child .o_search_panel_filter_value:last-child label').title.trim(),
            'A Status tooltip', "the last tag in the last facet have a tooltip");

        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_section:nth-of-type(3) .o_search_panel_section_header').textContent.trim(),
            'Attached To', "should have an 'attached to' section");
        assert.containsN(target, '.o_search_panel .o_search_panel_section:nth-of-type(3) .o_search_panel_filter_value', 4,
            "should have 4 types of models");
        assert.ok(find(target, '.o_search_panel_filter_value', "Task\n2"), "should display the correct number of records");
        assert.containsOnce(target.querySelector('.o_search_panel'), '.o_search_panel_section:nth-child(3) .o_search_panel_filter_value:contains("Not attached")', "should at least have a no-model element");
    });

    QUnit.test('document selector: render without facets & tags', async function (assert) {
        assert.expect(2);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (args.method === 'search_panel_select_multi_range') {
                    return Promise.resolve({values: [], });
                }
            },
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        assert.containsNone(target, '.o_search_panel .o_search_panel_filter_group',
            "shouldn't have any facet");
        assert.containsNone(target, '.o_search_panel .o_search_panel_filter_group .o_search_panel_filter_value',
            "shouldn't have any tag");
    });

    QUnit.test('document selector: render without related models', async function (assert) {
        assert.expect(4);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            domain: [['res_model', '=', false]],
        });

        assert.containsNone(target, '.o_search_panel .o_documents_selector_tags .o_search_panel_section_header',
            "shouldn't have a 'tags' section");
        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));
        assert.strictEqual(target.querySelector('.o_search_panel .o_search_panel_section:nth-of-type(3) .o_search_panel_section_header').textContent.trim(),
            'Attached To', "should have an 'attached to' section");
        assert.notOk([...target.querySelectorAll('.o_search_panel_filter_value')].find(el => el.innerText.trim() === 'Not attached'),
            "should not have an unattached document");
        assert.notOk([...target.querySelectorAll('.o_search_panel_filter_value')].find(el => el.innerText.trim() === 'Not a file'),
            "should not have an unattached document");
    });

    QUnit.test('document selector: filter on related model', async function (assert) {
        assert.expect(8);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(1) header'));

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value', 4, "should have 4 related models");

        // filter on 'Task'
        await click(find(target, '.o_search_panel_label_title', "Task"));
        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 2, "should have 3 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value', 4, "should have 4 related models");

        // filter on 'Attachment' (should be a disjunction)
        await click(find(target, '.o_search_panel_label_title', "Attachment"));

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 3, "should have 3 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value', 4, "should still have 4 related models");

        // remove both filters
        await click(find(target, '.o_search_panel_label_title', "Attachment"));
        await click(find(target, '.o_search_panel_label_title', "Task"));

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_section:nth-of-type(2) .o_search_panel_filter_value', 4, "should still have 4 related models");
    });

    QUnit.test('document selector: filter on attachments without related model', async function (assert) {
        assert.expect(8);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(1) header'));

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_filter_value', 4, "should have 4 related models");

        // filter on 'Not a file'
        await click(find(target, '.o_search_panel_label_title', "Not a file"));

        assert.containsOnce(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', "should have 1 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_filter_value', 4, "should still have 4 related models");

        // filter on 'Task'
        await click(find(target, '.o_search_panel_label_title', "Task"));
        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 3, "should have 4 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_filter_value', 4, "should still have 4 related models");

        // remove both filters
        await click(find(target, '.o_search_panel_label_title', "Not a file"));
        await click(find(target, '.o_search_panel_label_title', "Task"));

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.containsN(target, '.o_search_panel .o_search_panel_filter_value', 4, "should still have 4 related models");
    });

    QUnit.test('document selector: mix filter on related model and search filters', async function (assert) {
        assert.expect(10);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            searchViewArch: `
                    <search>
                        <filter name="owo" string="OwO" domain="[['name', 'in', ['yop', 'burp', 'pom', 'wip', 'zorro']]]"/>
                    </search>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(1) header'));

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 6, "should have 6 records in the renderer");
        assert.ok(
            find(target, '.o_search_panel_filter_value', "Task\n2"),
            "should display the correct number of records"
        );

        // filter on 'Task'
        await click(find(target, '.o_search_panel_label_title', "Task"));
        assert.strictEqual(target.querySelectorAll('.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)').length, 2, "should have 3 records in the renderer");

        // reload with a domain
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "OwO");

        assert.containsOnce(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 1, "should have 1 record in the renderer");
        assert.ok(
            find(target, '.o_search_panel_filter_value', "Task\n1"),
            "should display the correct number of records"
        );
        assert.ok(
            find(target, '.o_search_panel_filter_value', "Attachment\n1"),
            "should display the correct number of records"
        );

        // filter on 'Attachment'
        await click(find(target, '.o_search_panel_label_title', "Attachment"));

        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 2, "should have 2 records in the renderer");

        // reload without the domain
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "OwO");

        assert.strictEqual(target.querySelectorAll('.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)').length, 3, "should have 4 record in the renderer");
        assert.ok(
            find(target, '.o_search_panel_filter_value', "Task\n2"),
            "should display the correct number of records"
        );
        assert.ok(
            find(target, '.o_search_panel_filter_value', "Attachment\n1"),
            "should display the correct number of records"
        );
    });

    QUnit.test('document selector: selected tags are reset when switching between workspaces', async function (assert) {
        assert.expect(6);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/documents.document/web_search_read' && args.model === 'documents.document') {
                    assert.step(JSON.stringify(args.kwargs.domain || []));
                }
            },
        });

        // filter on records having tag Draft
        const input = find(target, '.o_search_panel_filter_value', 'Draft').querySelector('input');
        await click(input);

        assert.ok(input.checked,
            "tag selector should be checked");

        // switch to Workspace2
        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(3) header'));
        assert.ok(input.checked,
            "tag selector should not be checked anymore");

        assert.verifySteps([
            '[["folder_id","child_of",1]]',
            '["&",["folder_id","child_of",1],["tag_ids","in",[2]]]',
            '["&",["folder_id","child_of",2],["tag_ids","in",[2]]]',
        ]);
    });

    QUnit.test('document selector: should keep its selection when adding a tag', async function (assert) {
        assert.expect(5);

        // Make autocomplete input instantaneous
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
        

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_search_panel_category_value:nth-of-type(2) header'));

        // filter on records having tag Draft
        await click(find(target, '.o_search_panel_filter_value', 'Draft').querySelector('input'));

        assert.ok(find(target, '.o_search_panel_filter_value', 'Draft').querySelector('input').checked,
            "tag selector should be checked");

        assert.strictEqual(target.querySelectorAll('.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)').length,
            4, "should have records in the renderer");

        await click(target.querySelector('.o_kanban_record'), '.o_record_selector');

        const input = target.querySelector('.o_inspector_tags input');
        await editInput(input, null, 'stress');
        const autocompleteValues = target.querySelectorAll('.o_inspector_tags ul li');
        assert.strictEqual(autocompleteValues.length, 1,
            "should have an entry in the autocomplete dropdown");
        await click(autocompleteValues[0], 'a');
        assert.ok(find(target, '.o_search_panel_filter_value', 'Draft').querySelector('input').checked,
            "tag selector should still be checked");
        assert.strictEqual(target.querySelectorAll('.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)').length,
            4, "should still have the same records in the renderer");
    });

    QUnit.test('documents Kanban color widget', async function (assert) {
        assert.expect(4);
        
        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <field name="tag_ids" widget="documents_many2many_tags"/>
                    </div>
                </t></templates></kanban>`,
        });

        assert.containsN(target, '.o_field_documents_many2many_tags', 5,
            "All the records should have a color widget");

        assert.containsN(target, '.o_kanban_record:nth-of-type(3) .o_field_documents_many2many_tags .o_tag', 3,
            "This record should have 3 tags");

        assert.containsOnce(target, '.o_kanban_record:nth-of-type(3) .o_field_documents_many2many_tags .o_tag:nth-of-type(1) > span',
            "should have a span for color ball");

        assert.strictEqual(target.querySelector('.o_kanban_record:nth-of-type(3) .o_field_documents_many2many_tags .o_tag:nth-of-type(1) > span').style.backgroundColor,
            "rgb(108, 193, 237)", "should have the right color");
    });

    QUnit.test('kanban color widget without SearchPanel', async function (assert) {
        assert.expect(5);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `<kanban><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                        <field name="tag_ids" widget="documents_many2many_tags"/>
                    </div>
                </t></templates></kanban>`,
        });

        assert.containsN(target, '.o_field_documents_many2many_tags', 6,
            "All the records should have a color widget");

        assert.containsN(target, '.o_kanban_record:nth-of-type(3) .o_field_documents_many2many_tags .o_tag', 3,
            "Third record should have 3 tags");

        assert.containsOnce(target.querySelector('.o_kanban_record:nth-of-type(3) .o_field_documents_many2many_tags .o_tag:nth-of-type(1)'), '> span',
            "should have a span for color ball");
        assert.containsN(target.querySelector('.o_kanban_record:nth-of-type(3) .o_field_documents_many2many_tags'), '.o_tag_color_0', 3,
            "should have 3 spans for color ball with grey color by default");

        assert.strictEqual(target.querySelector('.o_kanban_record:nth-of-type(3) .o_field_documents_many2many_tags .o_tag:nth-of-type(1) > span').style.backgroundColor,
            "rgb(74, 79, 89)", "should have the right color");
    });

    QUnit.module("SearchPanel");

    QUnit.test('SearchPanel: can drag and drop in the search panel', async function (assert) {
        assert.expect(4);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <i class="fa fa-circle-thin o_record_selector"/>
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
            mockRPC: async function (route, args) {
                if (args.method === 'write' && args.model === 'documents.document') {
                    assert.deepEqual(
                        args.args[0],
                        [1, 2, 4],
                        "should write the right records");
                    assert.deepEqual(
                        args.args[1],
                        {folder_id: 2},
                        "should have written on a folder");
                    assert.step('documents.documents/write');
                }
            },
        });

        const yopRecord = find(target, '.o_kanban_record', 'yop').querySelector('.o_record_selector');
        // selects three records
        await click(yopRecord);
        await click(find(target, '.o_kanban_record', 'burp'), '.o_record_selector');
        await click(find(target, '.o_kanban_record', 'blip'), '.o_record_selector');

        // making sure that the documentInspector is already rendered as it is painted after the selection.
        await testUtils.nextTick();

        // starts the drag on a selected record
        const startEvent = new Event('dragstart', { bubbles: true, });
        const dataTransfer = new DataTransfer();
        startEvent.dataTransfer = dataTransfer;
        yopRecord.dispatchEvent(startEvent);

        // drop on the second search panel category (folder)
        const endEvent = new Event('drop', { bubbles: true, });
        endEvent.dataTransfer = dataTransfer;
        target.querySelector('.o_search_panel_category_value:nth-of-type(3)').dispatchEvent(endEvent);

        assert.verifySteps(['documents.documents/write']);
    });

    QUnit.test('SearchPanel: can not drag and hover over the search panel All selector', async function (assert) {
        assert.expect(1);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <i class="fa fa-circle-thin o_record_selector"/>
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (args.method === 'write' && args.model === 'documents.document') {
                    throw new Error('It should not be possible to drop a record on the All selector');
                }
            },
        });

        const yopRecord = find(target, '.o_kanban_record', 'yop').querySelector('.o_record_selector');
        const allSelector = target.querySelector('.o_search_panel_category_value:nth-of-type(1)');
        // selects one record
        await click(yopRecord);

        // starts the drag on a selected record
        const startEvent = new Event('dragstart', { bubbles: true, });
        const dataTransfer = new DataTransfer();
        startEvent.dataTransfer = dataTransfer;
        yopRecord.dispatchEvent(startEvent);

        const dragenterEvent = new Event('dragenter', { bubbles: true, });
        dragenterEvent.dataTransfer = dataTransfer;
        allSelector.dispatchEvent(dragenterEvent);
         assert.doesNotHaveClass(allSelector, 'o_drag_over_selector',
            "the All selector should not have the hover effect");

        // drop on the "All" search panel category
        // it should not add another write step.
        const dropEvent = new Event('drop', { bubbles: true, });
        dropEvent.dataTransfer = dataTransfer;
        allSelector.querySelector('header').dispatchEvent(dropEvent);
    });

    QUnit.test('SearchPanel: search panel should be resizable', async function (assert) {
        assert.expect(1);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area">
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        const searchPanel = target.getElementsByClassName('o_search_panel')[0];
        const resizeHandle = searchPanel.getElementsByClassName('o_resize')[0];
        const originalWidth = searchPanel.offsetWidth;

        await testUtils.dom.dragAndDrop(resizeHandle, searchPanel, { mousemoveTarget: document, mouseupTarget: document, position: 'right' });

        assert.ok(searchPanel.offsetWidth - originalWidth > 0,
            "width should be increased after resizing search panel");
    });

    QUnit.test("SearchPanel: regular user can not edit", async function (assert) {
        assert.expect(1);

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area">
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        assert.containsNone(target, ".o_documents_search_panel_section_edit");
    });

    QUnit.test("SearchPanel: can edit folders", async function (assert) {
        assert.expect(8);

        serviceRegistry.add(
            "user",
            makeFakeUserService((group) => group === "documents.group_documents_manager"),
            { force: true },
        );

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area">
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            mockRPC: async (route, args, performRpc) => {
                if (args.method === "set_parent_folder") {
                    assert.deepEqual(args.args[0], [2]);
                    assert.strictEqual(args.args[1], 1);
                    return performRpc('', {
                        model: args.model,
                        method: 'write',
                        args: [args.args[0], { parent_folder_id: args.args[1] }],
                    });
                }
            }
        });

        // Edition should not be enabled for "All" workspace
        assert.containsNone(target, ".o_search_panel_category_value:nth-of-type(1) .o_documents_search_panel_section_edit");

        // Test deletion on folder
        patchWithCleanup(kanban.env.services.action, {
            doAction(action) {
                assert.strictEqual(action, "documents.documents_folder_deletion_wizard_action");
            },
        });
        triggerEvent(target, '.o_search_panel_category_value:nth-of-type(2) .o_documents_search_panel_section_edit', 'click', {}, {skipVisibilityCheck: true});
        await nextTick();
        assert.containsOnce(target, ".o_search_panel_item_settings_popover");
        triggerEvent(target, ".o_search_panel_value_edit_delete", "click");

        // Test edition of folder settings
        patchWithCleanup(kanban.env.services.action, {
            doAction(action) {
                assert.deepEqual(action, {
                    res_model: "documents.folder",
                    res_id: 1,
                    name: "Edit",
                    type: "ir.actions.act_window",
                    target: "new",
                    views: [[false, "form"]],
                    context: {
                        create: false,
                    },
                });
            },
        });
        triggerEvent(target, '.o_search_panel_category_value:nth-of-type(2) .o_documents_search_panel_section_edit', 'click', {}, {skipVisibilityCheck: true});
        await nextTick();
        assert.containsOnce(target, ".o_search_panel_item_settings_popover");
        triggerEvent(target, ".o_search_panel_value_edit_edit", "click");

        // Test dragging a folder into another one
        const sourceFolder = find(target, ".o_search_panel_category_value:nth-of-type(3)");
        const targetFolder = find(target, ".o_search_panel_category_value:nth-of-type(2)");

        const startEvent = new Event('dragstart', { bubbles: true, });
        const dataTransfer = new DataTransfer();
        startEvent.dataTransfer = dataTransfer;
        sourceFolder.dispatchEvent(startEvent);

        const dropEvent = new Event('drop', { bubbles: true, });
        dropEvent.dataTransfer = dataTransfer;
        targetFolder.dispatchEvent(dropEvent);
        // Open folder dropdown
        click(target, '.o_search_panel_category_value:nth-of-type(2) header');
        await nextTick();
        assert.ok(find(targetFolder, ".o_search_panel_label_title", "Workspace3"));
    });

    QUnit.test("SearchPanel: can edit attributes", async function (assert) {
        assert.expect(2);

        serviceRegistry.add(
            "user",
            makeFakeUserService((group) => group === "documents.group_documents_manager"),
            { force: true },
        );

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area">
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        // Edition should work on tags
        const tag = find(target, '.o_search_panel_filter:nth-of-type(2) .o_search_panel_group_header:nth-of-type(1)', "●Priority");
        assert.containsOnce(tag, ".o_documents_search_panel_section_edit");

        // Edition should not work on res_model
        const resModel = find(target, '.o_search_panel_filter:nth-of-type(3) .o_search_panel_label_title:nth-of-type(1)', "Attachment");
        assert.containsNone(resModel, ".o_documents_search_panel_section_edit");
    });

    QUnit.module("Upload");

    QUnit.test("documents: upload with context", async function (assert) {
        assert.expect(4);

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs, (data) => {
            assert.strictEqual(data.get("res_model"), "project");
            assert.strictEqual(data.get("res_id"), "1");
            assert.step('xhrSend')
        });

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
            context: {
                default_res_model: 'project',
                default_res_id: 1,
            },
        });

        testUtils.file.dragoverFile($(target.querySelector(".o_kanban_renderer")), file);
        await nextTick();
        testUtils.file.dropFile($(target.querySelector('.o_documents_drop_over_zone')), file);
        await nextTick();
        assert.verifySteps(['xhrSend']);
    });

    QUnit.test('documents: upload progress bars', async function (assert) {
        assert.expect(5);

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs, () => assert.step('xhrSend'));

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        testUtils.file.dragoverFile($(target.querySelector(".o_kanban_renderer")), file);
        await nextTick();
        testUtils.file.dropFile($(target.querySelector('.o_documents_drop_over_zone')), file);
        await nextTick();
        assert.verifySteps(['xhrSend']);

        const progressEvent = new Event('progress', { bubbles: true, });
        progressEvent.loaded = 250000000;
        progressEvent.total = 500000000;
        progressEvent.lengthComputable = true;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);

        await nextTick();
        
        assert.strictEqual(target.querySelector('.o_file_upload_progress_text_left').textContent, "Uploading... (50%)",
            "the current upload progress should be at 50%");

        assert.containsOnce(target, '.o-file-upload-progress-bar-abort');

        progressEvent.loaded = 350000000;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);

        await nextTick();

        assert.strictEqual(target.querySelector('.o_file_upload_progress_text_right').textContent, "(350/500MB)",
            "the current upload progress should be at (350/500MB)");
    });

    QUnit.test('documents: max upload limit', async function (assert) {
        assert.expect(2);

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });
        Object.defineProperty(file, "size", {
            get: () => 67000001,
        });

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        patchWithCleanup(kanban.env.services.notification, {
            add(message, _option) {
                assert.strictEqual(message, "File is too large.",
                    "the notification message should be File is too large.");
            }
        });

        assert.strictEqual(file.size, 67000001, 'Upload file size is greater than upload limit');
        testUtils.file.dragoverFile($(target.querySelector(".o_kanban_renderer")), file);
        await nextTick();
        testUtils.file.dropFile($(target.querySelector('.o_documents_drop_over_zone')), file);
        await nextTick();
    });

    QUnit.test('documents: upload replace bars', async function (assert) {
        assert.expect(4);

        pyEnv['documents.document'].unlink(pyEnv['documents.document'].search([]));// reset incompatible setup
        const documentsDocumentId1 = pyEnv['documents.document'].create({
            folder_id: pyEnv['documents.folder'].search([])[0],
            name: 'request',
            type: 'empty',
        });

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        this.patchDocumentXHR([], () => assert.step('xhrSend'));

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area o_documents_attachment" data-id="${documentsDocumentId1}">
                        <field name="name"/>
                        <t t-set="fileUpload" t-value="getFileUpload(props.record)"/>
                        <i t-if="!fileUpload" class="fa fa-circle-thin o_record_selector" title="Select document"/>
                        <t t-else="">
                            <FileUploadProgressBar fileUpload="fileUpload"/>
                        </t>
                    </div>
                </t></templates></kanban>`,
        });

        await click(target.querySelector('.o_documents_attachment'));

        const fileInput = target.querySelector('.o_inspector_replace_input');
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        await nextTick();

        assert.verifySteps(['xhrSend']);

        assert.containsOnce(target, '.o_documents_attachment .o-file-upload-progress-bar-value',
            "there should be a progress bar");
        assert.containsOnce(target, '.o_documents_attachment .o-file-upload-progress-bar-abort',
            "there should be cancel upload cross");
    });

    QUnit.test('documents: upload multiple progress bars', async function (assert) {
        assert.expect(8);

        const file1 = await testUtils.file.createFile({
            name: 'text1.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });
        const file2 = await testUtils.file.createFile({
            name: 'text2.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });
        const file3 = await testUtils.file.createFile({
            name: 'text3.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs, () => assert.step('xhrSend'));

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        testUtils.file.dragoverFile($(target.querySelector(".o_kanban_renderer")), file1);
        await nextTick();
        testUtils.file.dropFile($(target.querySelector('.o_documents_drop_over_zone')), file1);
        await nextTick();

        // awaiting next tick as the file drop is not synchronous
        await nextTick();

        assert.verifySteps(['xhrSend']);
        assert.strictEqual(target.querySelector('.o_kanban_record:nth-of-type(1) .o_kanban_record_title span').textContent, 'text1.txt',
            "The first kanban card should be named after the file");

        testUtils.file.dragoverFile($(target.querySelector(".o_kanban_renderer")), [file2, file3]);
        await nextTick();
        testUtils.file.dropFiles($(target.querySelector('.o_documents_drop_over_zone')), [file2, file3]);
        await nextTick();

        // awaiting next tick as the file drop is not synchronous
        await nextTick();

        assert.verifySteps(['xhrSend']);
        assert.strictEqual(target.querySelector('.o_kanban_record:nth-of-type(2) .o_kanban_record_title span').textContent, '2 Files',
            "The new kanban card should be named after the amount of files");
        assert.containsN(target, '.o_kanban_progress_card', 2, "There should be 2 cards");

        // simulates 1st upload successful completion
        mockedXHRs[1].response = JSON.stringify({
            success: "All files uploaded"
        });
        mockedXHRs[1].dispatchEvent(new Event("load"));

        // awaiting next tick as the render of the notify card isn't synchronous
        await nextTick();

        assert.containsOnce(target, '.o_kanban_progress_card', "There should only be one card left");
    });

    QUnit.test('documents: notifies server side errors', async function (assert) {
        assert.expect(2);

        const file = await testUtils.file.createFile({
            name: 'text.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs);

        const kanban = await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
            <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                <div draggable="true" class="oe_kanban_global_area">
                    <field name="name"/>
                </div>
            </t></templates></kanban>`,
        });

        patchWithCleanup(kanban.env.services.notification, {
            add(message, _option) {
                assert.strictEqual(message, "One or more file(s) failed to upload",
                    "the notification message should be the response error message");
            }
        });

        testUtils.file.dragoverFile($(target.querySelector(".o_kanban_renderer")), file);
        await nextTick();
        testUtils.file.dropFile($(target.querySelector('.o_documents_drop_over_zone')), file);
        await nextTick();
        await nextTick();


        // simulates 1st upload server side error completion
        mockedXHRs[0].response = JSON.stringify({
            error: "One or more file(s) failed to upload"
        });
        mockedXHRs[0].status = 200;
        mockedXHRs[0].dispatchEvent(new Event("load"));
        await nextTick();

        assert.containsNone(target, '.o_kanban_progress_card', "There should be no upload card left");
    });

    QUnit.test('documents Kanban: displays youtube thumbnails', async function (assert) {
        assert.expect(1);

        pyEnv['documents.document'].create({
            folder_id: pyEnv['documents.folder'].search([])[0],
            name: 'youtubeVideo',
            type: 'url',
            url: 'https://youtu.be/Ayab6wZ_U1A'
        });

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div>
                        <i class="fa fa-circle-thin o_record_selector"/>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
        });

        await click(find(target, '.o_kanban_record', 'youtubeVideo'), '.o_record_selector');

        assert.strictEqual(
            target.querySelector('.o_documents_inspector img, .o_documents_single_preview .o_preview_available').dataset.src,
            "https://img.youtube.com/vi/Ayab6wZ_U1A/0.jpg",
            "the inspector should display the thumbnail of the youtube video");
    });

    QUnit.test('documents List: multi selection', async function (assert) {
        assert.expect(4);

        await createDocumentsView({
            type: 'list',
            resModel: 'documents.document',
            arch: `
                <tree js_class="documents_list">
                    <field name="type" invisible="1"/>
                    <field name="name"/>
                    <field name="partner_id"/>
                    <field name="owner_id"/>
                    <field name="type"/>
                </tree>`,
        });

        await click(target.querySelector('.o_data_row:nth-of-type(2)'));
        assert.ok(target.querySelector('.o_data_row:nth-of-type(2) input').checked, "the record should be selected");

        triggerEvent(target.querySelector('.o_data_row:nth-of-type(5)'), null, 'click', {
            shiftKey: true,
        });
        await nextTick();
        assert.containsN(target, '.o_list_record_selector input:checked', 4, "there should be 4 selected records");

        await click(target.querySelector('thead .o_list_record_selector input'));
        assert.containsN(target, '.o_list_record_selector input:checked', 6, "All (6) records should be selected");

        await click(target.querySelector('thead .o_list_record_selector input'));
        assert.containsNone(target, '.o_list_record_selector input:checked', "No record should be selected");
    });

    QUnit.test('documents List: selection using keyboard', async function (assert) {
        assert.expect(6);

        await createDocumentsView({
            type: 'list',
            resModel: 'documents.document',
            arch: `
            <tree js_class="documents_list">
                <field name="type" invisible="1"/>
                <field name="name"/>
                <field name="partner_id"/>
                <field name="owner_id"/>
                <field name="type"/>
            </tree>`,
        });

        let recordSelector = target.querySelector('.o_data_row:nth-of-type(5) .o_list_record_selector');
        recordSelector.focus();
        triggerEvent(recordSelector, null, 'keydown', {
            key: 'Enter',
        })
        await nextTick();
        assert.containsOnce(target, '.o_list_record_selector input:checked',
            "there should be 1 selected record");
        assert.ok(recordSelector.querySelector('input').checked,
            "the right record should be selected");

        recordSelector = target.querySelector('.o_data_row:nth-of-type(4) .o_list_record_selector');
        recordSelector.focus();
        triggerEvent(recordSelector, null, 'keydown', {
            key: 'Enter',
        })
        await nextTick();
        assert.containsOnce(target, '.o_list_record_selector input:checked',
            "there should be 1 selected record");
        assert.ok(recordSelector.querySelector('input').checked,
            "the right record should be selected");

        // Press Enter key with Shift key should select multiple records
        recordSelector = target.querySelector('.o_data_row:nth-of-type(3) .o_list_record_selector');
        recordSelector.focus();
        triggerEvent(recordSelector, null, 'keydown', {
            key: 'Enter',
            shiftKey: true,
        });
        await nextTick();
        assert.containsN(target, '.o_list_record_selector input:checked', 2,
            "there should be 2 selected records");

        recordSelector = target.querySelector('.o_data_row:nth-of-type(2) .o_list_record_selector');
        recordSelector.focus();
        triggerEvent(recordSelector, null, 'keydown', {
            key: ' ',
        });
        await nextTick();
        assert.containsN(target, '.o_list_record_selector input:checked', 3,
            "there should be 3 selected records");
    });

    QUnit.test('documents: Versioning', async function (assert) {
        assert.expect(13);

        const irAttachmentId1 = pyEnv['ir.attachment'].create({
            name: 'oldYoutubeVideo',
            create_date: '2019-12-09 14:13:21',
            create_uid: pyEnv.currentUserId,
        });
        const documentsDocumentId1 = pyEnv['documents.document'].create({
            folder_id: pyEnv['documents.folder'].search([])[0],
            name: 'newYoutubeVideo',
            type: 'url',
            url: 'https://youtu.be/Ayab6wZ_U1A',
            previous_attachment_ids: [irAttachmentId1],
        });

        await createDocumentsView({
            type: "kanban",
            resModel: 'documents.document',
            arch: `
                <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                    <div draggable="true" class="oe_kanban_global_area">
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`,
            async mockRPC(route, args) {
                if (args.model === 'ir.attachment' && args.method === 'unlink') {
                    assert.deepEqual(args.args[0], [irAttachmentId1],
                        "should unlink the right attachment");
                    assert.step('attachmentUnlinked');
                    return true;
                }
                if (args.model === 'documents.document' && args.method === 'write') {
                    assert.deepEqual(args.args[0], [documentsDocumentId1],
                        "should target the right document");
                    assert.deepEqual(args.args[1], {attachment_id: irAttachmentId1},
                        "should target the right attachment");
                    assert.step('attachmentRestored');
                    return true;
                }
            },
        });

        await click(target.querySelector('.o_kanban_record:nth-of-type(6)'));

        assert.strictEqual(target.querySelector('.o_inspector_history_name').textContent, 'oldYoutubeVideo',
            "should display the correct record name");
        assert.strictEqual(target.querySelector('.o_inspector_history_create_name').textContent, 'Your Company, Mitchell Admin',
            "should display the correct name");
        assert.strictEqual(
            target.querySelector('.o_inspector_history_info_date').textContent,
            str_to_datetime('2019-12-09 14:13:21').toLocaleDateString(),
            "should display the correct date"
        );

        assert.containsOnce(target, '.o_inspector_history_item_restore',
            "There should be one restore button");
        assert.containsOnce(target, '.o_inspector_history_item_download',
            "There should be one download button");
        assert.containsOnce(target, '.o_inspector_history_item_delete',
            "There should be one delete button");

        await click(target.querySelector('.o_inspector_history_item_restore'));
        assert.verifySteps(['attachmentRestored']);
        await click(target.querySelector('.o_inspector_history_item_delete'));
        assert.verifySteps(['attachmentUnlinked']);
    });

    QUnit.test("store and retrieve active category value", async function (assert) {
        assert.expect(8);

        let expectedActiveId = 3;
        const storageKey = "searchpanel_documents.document_folder_id";
        const ramStorage = makeRAMLocalStorage();
        const getItem = ramStorage.getItem.bind(ramStorage);
        const setItem = ramStorage.setItem.bind(ramStorage);
        const storage = Object.assign(ramStorage, {
            getItem(key) {
                const value = getItem(key);
                if (key === storageKey) {
                    assert.step(`storage get ${value}`);
                }
                return value;
            },
            setItem(key, value) {
                if (key === storageKey) {
                    assert.step(`storage set ${value}`);
                }
                setItem(key, value);
            },
        });
        storage.setItem(storageKey, expectedActiveId);
        patchWithCleanup(browser, {
            localStorage: storage,
        });
        await createDocumentsView({
            type: "kanban",
            resModel: "documents.document",
            arch: `
                <kanban js_class="documents_kanban">
                    <templates>
                        <div t-name="kanban-box">
                            <field name="name"/>
                        </div>
                    </templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (route === '/web/dataset/call_kw/documents.document/web_search_read' && args.model === 'documents.document') {
                    assert.deepEqual(args.kwargs.domain, [["folder_id", "child_of", expectedActiveId]]);
                }
            },
        });

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth-of-type(1) .active");

        expectedActiveId = 2;
        await click(target, ".o_search_panel_category_value:nth-of-type(3) header");

        assert.verifySteps([
            "storage set 3", // Manual set for initial value
            "storage get 3",
            "storage set 2", // Set on toggle
        ]);
    });

    QUnit.test("retrieved category value does not exist", async function (assert) {
        assert.expect(5);

        const storageKey = "searchpanel_documents.document_folder_id";
        const ramStorage = makeRAMLocalStorage();
        const getItem = ramStorage.getItem.bind(ramStorage);
        const storage = Object.assign(ramStorage, {
            getItem(key) {
                const value = getItem(key);
                if (key === storageKey) {
                    assert.step(`storage get ${value}`);
                }
                return value;
            },
        });
        storage.setItem(storageKey, 343);
        patchWithCleanup(browser, {
            localStorage: storage,
        });
        await createDocumentsView({
            type: "kanban",
            resModel: "documents.document",
            arch: `
                <kanban js_class="documents_kanban">
                    <templates>
                        <div t-name="kanban-box">
                            <field name="name"/>
                        </div>
                    </templates>
                </kanban>`,
            async mockRPC(route, args) {
                if (route === '/web/dataset/call_kw/documents.document/web_search_read' && args.model === 'documents.document') {
                    assert.deepEqual(args.kwargs.domain, [["folder_id", "child_of", 1]]);
                }
            },
        });

        assert.containsOnce(target, ".o_search_panel_category_value .active");
        assert.containsOnce(target, ".o_search_panel_category_value:nth(1) .active");

        assert.verifySteps(["storage get 343"]);
    });
});
});
