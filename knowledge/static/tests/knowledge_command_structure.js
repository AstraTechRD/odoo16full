/** @odoo-module */

import { ArticlesStructureBehavior } from "@knowledge/components/behaviors/articles_structure_behavior/articles_structure_behavior";
import { click, getFixture, makeDeferred, nextTick } from "@web/../tests/helpers/utils";
import { patch, unpatch } from "@web/core/utils/patch";
import { makeFakeMessagingServiceForKnowledge } from "@knowledge/../tests/mock_services";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");
const { onMounted } = owl;

const articlesStructureSearch = {
    records: [
        { id: 1, display_name: 'My Article', parent_id: false },
        { id: 2, display_name: 'Child 1', parent_id: [1, 'My Article'] },
        { id: 3, display_name: 'Child 2', parent_id: [1, 'My Article'] },
    ]
};

const articlesIndexSearch = {
    records: articlesStructureSearch.records.concat([
        { id: 4, display_name: 'Grand-child 1', parent_id: [2, 'Child 1'] },
        { id: 5, display_name: 'Grand-child 2', parent_id: [2, 'Child 1'] },
        { id: 6, display_name: 'Grand-child 3', parent_id: [3, 'Child 2'] },
    ])
};

/**
 * Insert an article structure (index or outline) in the target node. This will
 * guarantee that the structure behavior is fully mounted before continuing.
 * @param {HTMLElement} editable
 * @param {HTMLElement} target
 * @param {boolean} childrenOnly
 */
const insertArticlesStructure = async (editable, target, childrenOnly) => {
    const articleStructureMounted = makeDeferred();
    const wysiwyg = $(editable).data('wysiwyg');
    patch(ArticlesStructureBehavior.prototype, 'ARTICLE_STRUCTURE_PATCH_TEST', {
        setup() {
            this._super(...arguments);
            onMounted(() => {
                articleStructureMounted.resolve();
                unpatch(ArticlesStructureBehavior.prototype, 'ARTICLE_STRUCTURE_PATCH_TEST');
            });
        }
    });
    const selection = document.getSelection();
    selection.removeAllRanges();
    const range = new Range();
    range.setStart(target, 0);
    range.setEnd(target, 0);
    selection.addRange(range);
    await nextTick();
    wysiwyg._insertArticlesStructure(childrenOnly);
    await articleStructureMounted;
    await nextTick();
};

let fixture;
let type;
let resModel;
let serverData;
let arch;

QUnit.module("Knowledge - Articles Structure Command", (hooks) => {
    hooks.beforeEach(() => {
        fixture = getFixture();
        type = "form";
        resModel = "knowledge_article";
        serverData = {
            models: {
                knowledge_article: {
                    fields: {
                        display_name: {string: "Displayed name", type: "char"},
                        body: {string: "Body", type: 'html'},
                    },
                    records: [{
                        id: 1,
                        display_name: "My Article",
                        body: '<p class="test_target"><br/></p>',
                    }]
                }
            }
        };
        arch = '<form js_class="knowledge_article_view_form">' +
            '<sheet>' +
                '<div t-ref="tree"/>' +
                '<div t-ref="root">' +
                    '<div class="o_knowledge_editor d-flex flex-grow-1">' +
                        '<field name="body" widget="html"/>' +
                    '</div>' +
                '</div>' +
            '</sheet>' +
        '</form>';
        setupViewRegistries();
        serviceRegistry.add('messaging', makeFakeMessagingServiceForKnowledge());
    });
    QUnit.test('Check Articles Structure is correctly built', async function (assert) {
        assert.expect(3);

        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1,
            mockRPC(route, args) {
                if (route === '/web/dataset/search_read' && args.model === 'knowledge.article') {
                    return Promise.resolve(articlesStructureSearch);
                }
            }
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        const target = editable.querySelector('p.test_target');
        await insertArticlesStructure(editable, target, true);

        // /articles_structure only considers the direct children - "Child 1" and "Child 2"
        assert.containsN(editable, '.o_knowledge_articles_structure_content ol a', 2);
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 1")');
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 2")');
    });
    QUnit.test('Check Articles Index is correctly built - and updated', async function (assert) {
        assert.expect(8);

        let searchReadCallCount = 0;
        await makeView({
            type,
            resModel,
            serverData,
            arch,
            resId: 1,
            mockRPC(route, args) {
                if (route === '/web/dataset/search_read' && args.model === 'knowledge.article') {
                    if (searchReadCallCount === 0) {
                        searchReadCallCount++;
                        return Promise.resolve(articlesIndexSearch);
                    } else {
                        // return updated result (called when clicking on the refresh button)
                        return Promise.resolve({
                            records: articlesIndexSearch.records.concat([
                                { id: 7, display_name: 'Grand-child 4', parent_id: [3, 'Child 2'] },
                            ])
                        });
                    }
                }
            }
        });

        const editable = fixture.querySelector('.odoo-editor-editable');
        const target = editable.querySelector('p.test_target');
        await insertArticlesStructure(editable, target, false);

        // /articles_index considers whole children - "Child 1" and "Child 2" and then their respective children
        assert.containsN(editable, '.o_knowledge_articles_structure_content ol a', 5);
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 1")');
        assert.containsOnce(editable, '.o_knowledge_articles_structure_content ol a:contains("Child 2")');
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 1") ol a:contains("Grand-child 1")');
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 1") ol a:contains("Grand-child 2")');
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 2") ol a:contains("Grand-child 3")');

        // clicking on update yields an additional Grand-child (see 'mockRPC' here above)
        // make sure our structure is correctly updated
        await click(editable, '.o_knowledge_behavior_type_articles_structure button[title="Update"]');
        await nextTick();

        assert.containsN(editable, '.o_knowledge_articles_structure_content ol a', 6);
        assert.containsOnce(editable,
            '.o_knowledge_articles_structure_content ol:contains("Child 2") ol a:contains("Grand-child 4")');

    });
});
