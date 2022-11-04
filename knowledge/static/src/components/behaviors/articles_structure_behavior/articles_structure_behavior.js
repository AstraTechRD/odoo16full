/** @odoo-module */

import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { useService } from "@web/core/utils/hooks";
import { qweb as QWeb }  from "web.core";

const {
    markup,
    useEffect,
    useState,
    onMounted,
    onPatched,
    onWillPatch } = owl;

let observerId = 0;

/**
 * It creates a listing of children of this article.
 *
 * It is used by 2 different commands:
 * - /index that only list direct children
 * - /outline that lists all children
 */
export class ArticlesStructureBehavior extends AbstractBehavior {
    setup () {
        super.setup();
        this.rpc = useService('rpc');
        this.actionService = useService('action');
        this.observerId = observerId++;

        if (this.props.content) {
            this.state = useState({
                loading: false,
                refreshing: false,
            });
            this.props.content = markup(this.props.content);
        } else {
            this.state = useState({
                loading: true,
                refreshing: false,
            });
            onMounted(async () => {
                this.props.content = await this._renderArticlesStructure();
                this.state.loading = false;
            });
        }

        useEffect(() => {
            const onClick = this._onArticleLinkClick.bind(this);
            const links = this.props.anchor.querySelectorAll('.o_knowledge_article_structure_link');
            links.forEach(link => link.addEventListener('click', onClick));
            return () => {
                links.forEach(link => link.removeEventListener('click', onClick));
            };
        });

        useEffect(() => {
            const onDrop = event => {
                event.preventDefault();
                event.stopPropagation();
            };
            this.props.anchor.addEventListener('drop', onDrop);
            return () => {
                this.props.anchor.removeEventListener('drop', onDrop);
            };
        });

        onWillPatch(() => {
            this.editor.observerUnactive(`knowledge_article_structure_id_${this.observerId}`);
        });
        onPatched(() => {
            this.editor.idSet(this.props.anchor);
            this.editor.observerActive(`knowledge_article_structure_id_${this.observerId}`);
        });
    }

    /**
     * @returns {OdooEditor}
     */
    get editor () {
        return this.props.wysiwyg.odooEditor;
    }

    /**
     * @returns {HTMLElement}
     */
    async _renderArticlesStructure () {
        const articleId = this.props.record.data.id;
        const allArticles = await this._fetchAllArticles(articleId);
        return markup(QWeb.render('knowledge.articles_structure', {
            'articles': this._buildArticlesStructure(articleId, allArticles)
        }));
    }

    /**
     * @returns {Array[Object]}
     */
    async _fetchAllArticles (articleId) {
        const selector = 'o_knowledge_articles_structure_children_only';
        const domain = [
            ['parent_id', this.props.anchor.classList.contains(selector) ? '=' : 'child_of', articleId],
            ['is_article_item', '=', false]
        ];
        const { records } = await this.rpc('/web/dataset/search_read', {
            model: 'knowledge.article',
            fields: ['id', 'display_name', 'parent_id'],
            domain,
            sort: 'sequence',
        });
        return records;
    }

    /**
     * Transforms the flat search_read result into a parent/children articles hierarchy.
     *
     * @param {Integer} parentId
     * @param {Array} allArticles
     * @returns {Array[Object]} articles structure
     */
    _buildArticlesStructure (parentId, allArticles) {
        const articles = [];
        for (const article of allArticles) {
            if (article.parent_id && article.parent_id[0] === parentId) {
                articles.push({
                    id: article.id,
                    name: article.display_name,
                    child_ids: this._buildArticlesStructure(article.id, allArticles),
                });
            }
        }
        return articles;
    }

    // Listeners:

    /**
     * Opens the article in the side tree menu.
     *
     * @param {Event} event
     */
    async _onArticleLinkClick (event) {
        event.preventDefault();
        this.actionService.doAction('knowledge.ir_actions_server_knowledge_home_page', {
            additionalContext: {
                res_id: parseInt(event.target.getAttribute('data-oe-nodeid'))
            }
        });
    }

    /**
     * @param {Event} event
     */
    async _onRefreshBtnClick (event) {
        event.stopPropagation();
        this.state.refreshing = true;
        this.props.content = await this._renderArticlesStructure();
        this.state.refreshing = false;
    }
}

ArticlesStructureBehavior.template = "knowledge.ArticlesStructureBehavior";
ArticlesStructureBehavior.props = {
    ...AbstractBehavior.props,
    content: { type: String, optional: true },
};
