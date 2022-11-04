/** @odoo-module */

import { dom } from "web.test_utils";
import { createDocumentsView } from "@documents/../tests/documents_test_utils";
import { startServer } from "@mail/../tests/helpers/test_utils";
import {
    click,
    getFixture,
    mockDownload,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { fileUploadService } from "@web/core/file_upload/file_upload_service";
import { browser } from "@web/core/browser/browser";
import { DocumentsSearchPanel } from "@documents/views/search/documents_search_panel";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { DocumentsKanbanRenderer } from "@documents/views/kanban/documents_kanban_renderer";

const find = dom.find;
const serviceRegistry = registry.category("services");

let target;

QUnit.module(
    "documents_spreadsheet kanban",
    {
        beforeEach() {
            setupViewRegistries();
            target = getFixture();
            serviceRegistry.add("file_upload", fileUploadService);
            serviceRegistry.add("documents_pdf_thumbnail", {
                start() {
                    return {
                        enqueueRecords: () => {},
                    };
                },
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
            // Due to the search panel allowing double clicking on elements, the base
            // methods have a debounce time in order to not do anything on dblclick.
            // This patch removes those features
            patchWithCleanup(DocumentsSearchPanel.prototype, {
                toggleCategory() {
                    return SearchPanel.prototype.toggleCategory.call(this, ...arguments);
                },
                toggleFilterGroup() {
                    return SearchPanel.prototype.toggleFilterGroup.call(this, ...arguments);
                },
                toggleFilterValue() {
                    return SearchPanel.prototype.toggleFilterValue.call(this, ...arguments);
                },
            });
        },
    },
    () => {
        QUnit.test("download spreadsheet from the document inspector", async function (assert) {
            assert.expect(4);
            patchWithCleanup(browser, { setInterval: (fn) => fn(), clearInterval: () => {} });
            const pyEnv = await startServer();
            const documentsFolderId1 = pyEnv["documents.folder"].create({
                display_name: "Workspace1",
                has_write_access: true,
            });
            pyEnv["documents.document"].create({
                name: "My spreadsheet",
                raw: "{}",
                is_favorited: false,
                folder_id: documentsFolderId1,
                handler: "spreadsheet",
            });
            mockDownload((options) => {
                assert.step(options.url);
                assert.ok(options.data.zip_name);
                assert.ok(options.data.files);
            });
            await createDocumentsView({
                type: "kanban",
                resModel: "documents.document",
                arch: `
              <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                  <div>
                      <i class="fa fa-circle-thin o_record_selector"/>
                      <field name="name"/>
                      <field name="handler"/>
                  </div>
              </t></templates></kanban>`,
                serverData: { models: pyEnv.getData(), views: {} },
            });

            await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
            await click(target, "button.o_inspector_download");
            await nextTick();
            assert.verifySteps(["/spreadsheet/xlsx"]);
        });

        QUnit.test("thumbnail size in document side panel", async function (assert) {
            assert.expect(9);
            const pyEnv = await startServer();
            const documentsFolderId1 = pyEnv["documents.folder"].create({
                display_name: "Workspace1",
                has_write_access: true,
            });
            pyEnv["documents.document"].create([
                {
                    name: "My spreadsheet",
                    raw: "{}",
                    is_favorited: false,
                    folder_id: documentsFolderId1,
                    handler: "spreadsheet",
                },
                {
                    name: "",
                    raw: "{}",
                    is_favorited: true,
                    folder_id: documentsFolderId1,
                    handler: "spreadsheet",
                },
                {
                    name: "",
                    raw: "{}",
                    folder_id: documentsFolderId1,
                    handler: "spreadsheet",
                },
            ]);
            await createDocumentsView({
                type: "kanban",
                resModel: "documents.document",
                arch: `
              <kanban js_class="documents_kanban"><templates><t t-name="kanban-box">
                  <div>
                      <i class="fa fa-circle-thin o_record_selector"/>
                      <field name="name"/>
                      <field name="handler"/>
                  </div>
              </t></templates></kanban>
          `,
                serverData: { models: pyEnv.getData(), views: {} },
            });
            await click(target, ".o_kanban_record:nth-of-type(1) .o_record_selector");
            assert.containsOnce(target, ".o_documents_inspector_preview .o_document_preview");
            assert.equal(
                find(target, ".o_documents_inspector_preview .o_document_preview img").dataset.src,
                "/documents/image/1/268x130?field=thumbnail&unique="
            );
            await click(target, ".o_kanban_record:nth-of-type(2) .o_record_selector");
            assert.containsN(target, ".o_documents_inspector_preview .o_document_preview", 2);
            let previews = target.querySelectorAll(
                ".o_documents_inspector_preview .o_document_preview img"
            );
            assert.equal(
                previews[0].dataset.src,
                "/documents/image/1/120x130?field=thumbnail&unique="
            );
            assert.equal(
                previews[1].dataset.src,
                "/documents/image/2/120x130?field=thumbnail&unique="
            );
            await click(target, ".o_kanban_record:nth-of-type(3) .o_record_selector");
            assert.containsN(target, ".o_documents_inspector_preview .o_document_preview", 3);
            previews = target.querySelectorAll(
                ".o_documents_inspector_preview .o_document_preview img"
            );
            assert.equal(
                previews[0].dataset.src,
                "/documents/image/1/120x75?field=thumbnail&unique="
            );
            assert.equal(
                previews[1].dataset.src,
                "/documents/image/2/120x75?field=thumbnail&unique="
            );
            assert.equal(
                previews[2].dataset.src,
                "/documents/image/3/120x75?field=thumbnail&unique="
            );
        });
    }
);
