/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
const { Component, useRef, onMounted } = owl;
import { _t } from 'web.core';

class MoveArticleDialog extends Component {
    setup() {
        this.size = 'md';
        this.title = _t("Move an Article");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.user = useService("user");

        this.input = useRef("input");
        onMounted(() => this.initSelect2());
    }

    _onMoveArticleClick() {
        const $input = $(this.input.el);
        const selected = $input.select2('data').id;
        const params = { article_id: this.props.articleId };
        if (typeof selected === 'number') {
            params.target_parent_id = selected;
        } else {
            params.newCategory = selected;
            params.oldCategory = this.props.category;
        }

        this.props.moveArticle({...params,
            onSuccess: () => {
                this.props.close();
                // ADSC: maybe remove when tree component
                this.props.reloadTree(this.props.articleId, '/knowledge/tree_panel');
            },
            onReject: () => {}
        });
    }

    get loggedUserPicture() {
        return `/web/image?model=res.users&field=avatar_128&id=${this.user.userId}`;
    }

    initSelect2() {
        const cache = {
            results: [{
                text: _t('Categories'),
                children: [{
                    id: 'private',
                    text: _t('Private'),
                    selected: true
                }, {
                    id: 'workspace',
                    text: _t('Workspace')
                }]
            }]
        };

        const $input = $(this.input.el);
        $input.select2({
            containerCssClass: 'o_knowledge_select2',
            dropdownCssClass: 'o_knowledge_select2',
            data: cache, // Pre-fetched records
            ajax: {
                /**
                 * @param {String} term
                 * @returns {Object}
                 */
                data: term => {
                    return { term };
                },
                /**
                 * @param {Object} params - parameters
                 */
                transport: async params => {
                    const { term } = params.data;
                    const results = await this.orm.call(
                        'knowledge.article',
                        'get_valid_parent_options',
                        [this.props.articleId],
                        { search_term: term }
                    );
                    params.success({ term, results });
                },
                /**
                 * @param {Object} data
                 * @returns {Object}
                 */
                processResults: function (data) {
                    const records = { results: [] };
                    for (const result of cache.results) {
                        if (typeof result.children === 'undefined') {
                            records.results.push(result);
                            continue;
                        }
                        const children = result.children.filter(child => {
                            const text = child.text.toLowerCase();
                            const term = data.term.toLowerCase();
                            return text.indexOf(term) >= 0;
                        });
                        if (children.length > 0) {
                            records.results.push({...result, children});
                        }
                    }
                    if (data.results.length > 0) {
                        records.results.push({
                            text: _t('Articles'),
                            children: data.results.map(record => {
                                return {
                                    id: record.id,
                                    text: record.display_name,
                                    subject: record.root_article_id[1],
                                };
                            })
                        });
                    }
                    return records;
                },
            },
            /**
             * @param {Object} data
             * @param {JQuery} container
             * @param {Function} escapeMarkup
             */
            formatSelection: (data, container, escapeMarkup) => {
                const markup = [];
                if (data.id === 'private') {
                    const src = escapeMarkup(this.loggedUserPicture);
                    markup.push(`<img src="${src}" class="rounded-circle me-1"/>`);
                }
                markup.push(escapeMarkup(data.text));
                return markup.join('');
            },
            /**
             * @param {Object} result
             * @param {JQuery} container
             * @param {Object} query
             * @param {Function} escapeMarkup
             */
            formatResult: (result, container, query, escapeMarkup) => {
                const { text, subject } = result;
                const markup = [];
                window.Select2.util.markMatch(text, query.term, markup, escapeMarkup);
                if (result.id === 'private') {
                    const src = escapeMarkup(this.loggedUserPicture);
                    markup.unshift(`<img src="${src}" class="rounded-circle me-1"/>`);
                }
                if (subject && subject !== text) {
                    markup.push(`<span class="text-ellipsis small">  -  ${escapeMarkup(subject)}</span>`);
                }
                return markup.join('');
            },
        });
    }
}

MoveArticleDialog.template = "knowledge.MoveArticleDialog";
MoveArticleDialog.components = { Dialog };
MoveArticleDialog.props = {
    close: Function,
    articleName: String,
    articleId: Number,
    category: String,
    moveArticle: Function,
    reloadTree: Function,
};

export default MoveArticleDialog;
