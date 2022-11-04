/** @odoo-module **/

import { PdfManager } from '@documents/owl/components/pdf_manager/pdf_manager';
import {
    getFixture,
    nextTick,
    click,
    patchWithCleanup,
    mount,
} from '@web/../tests/helpers/utils';
import { makeTestEnv } from '@web/../tests/helpers/mock_env';
import { notificationService } from '@web/core/notifications/notification_service';
import { uiService } from '@web/core/ui/ui_service';
import { registry } from "@web/core/registry";
const serviceRegistry = registry.category("services");

let env;
let target;

QUnit.module('documents', {}, function () {
QUnit.module('documents_pdf_manager_tests.js', {
    async beforeEach() {
        patchWithCleanup(PdfManager.prototype, {
            async _loadAssets() { },
            async _getPdf() {
                return {
                    getPage: number => ({ number }),
                    numPages: 6,
                };
            },
            async _renderCanvas(page, { width, height }) {
                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                return canvas;
            },
        });
        serviceRegistry.add('notification', notificationService);
        serviceRegistry.add('ui', uiService);
        env = await makeTestEnv( { serviceRegistry });
        target = getFixture();
    },
}, () => {
    QUnit.test('Pdf Manager basic rendering', async function (assert) {
        assert.expect(9);

        await mount(PdfManager, target, { env, props: {
            documents: [
                { id: 1, name: 'yop', mimetype: 'application/pdf', available_rule_ids: [1, 2] },
                { id: 2, name: 'blip', mimetype: 'application/pdf', available_rule_ids: [1] },
            ],
            rules: [
                { id: 1, display_name: 'rule1', note: 'note1', limited_to_single_record: false },
                { id: 2, display_name: 'rule2', limited_to_single_record: false },
            ],
            onProcessDocuments: () => {},
            close: () => {},
        }});

        await nextTick();

        assert.containsOnce(target, '.o_documents_pdf_manager_top_bar',
            "There should be one top bar");
        assert.containsOnce(target, '.o_documents_pdf_page_viewer',
            "There should be one page viewer");

        assert.containsOnce($(target), '.o_pdf_manager_button:contains(Split)',
            "There should be one Split button");
        assert.containsOnce($(target), '.o_pdf_manager_button:contains(Add File)',
            "There should be one Add File button");
        assert.containsN(target, '.o_pdf_rule_buttons', 2,
            "There should be 2 rule buttons");

        assert.containsOnce(target, '.o_pdf_separator_activated',
            "There should be one active separator");
        assert.containsN(target, '.o_pdf_page', 12,
            "There should be 12 pages");
        assert.containsN(target, '.o_documents_pdf_button_wrapper', 12,
            "There should be 12 button wrappers");

        assert.containsN(target, '.o_pdf_group_name_wrapper', 2,
            "There should be 2 name plates");
    });

    QUnit.test('Pdf Manager: page interactions', async function (assert) {
        assert.expect(4);

        await mount(PdfManager, target, { env, props: {
            documents: [
                { id: 1, name: 'yop', mimetype: 'application/pdf', available_rule_ids: [1, 2] },
                { id: 2, name: 'blip', mimetype: 'application/pdf', available_rule_ids: [1] },
            ],
            rules: [],
            onProcessDocuments: () => {},
            close: () => {},
        }});
        await nextTick();

        assert.containsOnce(target, '.o_pdf_separator_activated',
            "There should be one active separator");

        await click(target.querySelectorAll('.o_page_splitter_wrapper')[1]);
        await nextTick();

        assert.containsN(target, '.o_pdf_separator_activated', 2,
            "There should be 2 active separator");

        assert.containsN(target, '.o_pdf_page_selected', 12, "There should be 5 selected pages");
        await click(target.querySelectorAll('.o_documents_pdf_page_selector')[3]);
        assert.containsN(target, '.o_pdf_page_selected', 11, "There should be 5 selected pages");
    });

    QUnit.test('Pdf Manager: drag & drop', async function (assert) {
        assert.expect(4);

        await mount(PdfManager, target, { env, props: {
            documents: [
                { id: 1, name: 'yop', mimetype: 'application/pdf', available_rule_ids: [1, 2] },
            ],
            rules: [],
            onProcessDocuments: () => {},
            close: () => {},
        }});
        await nextTick();

        assert.containsN(target, '.o_pdf_separator_activated', 5,
            "There should be 5 active separator");
        assert.containsOnce(target.querySelectorAll('.o_documents_pdf_page_frame')[2], '.o_pdf_name_display',
            "The third page should have a name plate");

        const startEvent = new Event('dragstart', { bubbles: true, });
        const dataTransfer = new DataTransfer();
        startEvent.dataTransfer = dataTransfer;
        target.querySelectorAll('.o_documents_pdf_canvas_wrapper')[5].dispatchEvent(startEvent);

        const endEvent = new Event('drop', { bubbles: true, });
        endEvent.dataTransfer = dataTransfer;
        target.querySelectorAll('.o_documents_pdf_canvas_wrapper')[1].dispatchEvent(endEvent);

        await nextTick();

        assert.containsN(target, '.o_pdf_separator_activated', 4,
            "There should be 4 active separator");
        assert.containsNone(target.querySelectorAll('.o_documents_pdf_page_frame')[2], '.o_pdf_name_display',
            "The third page shouldn't have a name plate");
    });
});
});
