/** @odoo-module **/

import { ComponentWrapper } from 'web.OwlCompatibility';
import { qweb as QWeb, _t } from 'web.core';
import Wysiwyg from 'web_editor.wysiwyg';
import { KnowledgeArticleLinkModal } from './wysiwyg/knowledge_article_link.js';
import { PromptEmbeddedViewNameDialogWrapper } from '../components/prompt_embedded_view_name_dialog/prompt_embedded_view_name_dialog.js';
import { preserveCursor } from '@web_editor/js/editor/odoo-editor/src/OdooEditor';

Wysiwyg.include({
    /**
     * @override
     */
    init: function (parent, options) {
        if (options.knowledgeCommands) {
            /**
             * knowledgeCommands is a view option from a field_html that
             * indicates that knowledge-specific commands should be loaded.
             * powerboxFilters is an array of functions used to filter commands
             * displayed in the powerbox.
             */
            options.powerboxFilters = options.powerboxFilters ? options.powerboxFilters : [];
            options.powerboxFilters.push(this._filterKnowledgeCommandGroupInTable);
            options.powerboxFilters.push(this._filterKnowledgeCommandGroupInTemplate);
        }
        this._super.apply(this, arguments);
    },
    /**
     * Prevent usage of commands from the group "Knowledge" inside the tables.
     * @param {Array[Object]} commands commands available in this wysiwyg
     * @returns {Array[Object]} commands which can be used after the filter was applied
     */
    _filterKnowledgeCommandGroupInTable: function (commands) {
        let anchor = document.getSelection().anchorNode;
        if (anchor.nodeType !== Node.ELEMENT_NODE) {
            anchor = anchor.parentElement;
        }
        if (anchor && anchor.closest('table')) {
            commands = commands.filter(command => command.category !== 'Knowledge');
        }
        return commands;
    },
    /**
     * Prevent usage of commands from the group "Knowledge" inside the block
     * inserted by the /template Knowledge command. The content of a /template
     * block is destined to be used in @see OdooEditor in modules other than
     * Knowledge, where knowledge-specific commands may not be available.
     * i.e.: prevent usage /template in a /template block
     *
     * @param {Array[Object]} commands commands available in this wysiwyg
     * @returns {Array[Object]} commands which can be used after the filter was applied
     */
    _filterKnowledgeCommandGroupInTemplate: function (commands) {
        let anchor = document.getSelection().anchorNode;
        if (anchor.nodeType !== Node.ELEMENT_NODE) {
            anchor = anchor.parentElement;
        }
        if (anchor && anchor.closest('.o_knowledge_content')) {
            commands = commands.filter(command => command.category !== 'Knowledge');
        }
        return commands;
    },
    /**
     * @override
     * @returns {Array[Object]}
     */
    _getPowerboxOptions: function () {
        const options = this._super();
        const {commands, categories} = options;
        categories.push({ name: 'Media', priority: 50 });
        commands.push({
            category: 'Media',
            name: _t('Article'),
            priority: 10,
            description: _t('Link an article.'),
            fontawesome: 'fa-file',
            callback: () => {
                this._insertArticleLink();
            },
        });
        if (this.options.knowledgeCommands) {
            categories.push({ name: 'Knowledge', priority: 10 });
            commands.push({
                category: 'Knowledge',
                name: _t('File'),
                priority: 20,
                description: _t('Embed a file.'),
                fontawesome: 'fa-file',
                callback: () => {
                    this.openMediaDialog({
                        noVideos: true,
                        noImages: true,
                        noIcons: true,
                        noDocuments: true,
                        knowledgeDocuments: true,
                    });
                }
            }, {
                category: 'Knowledge',
                name: _t('Template'),
                priority: 10,
                description: _t('Add a template section.'),
                fontawesome: 'fa-pencil-square',
                callback: () => {
                    this._insertTemplate();
                },
            }, {
                category: 'Knowledge',
                name: _t('Table Of Content'),
                priority: 30,
                description: _t('Add a table of content.'),
                fontawesome: 'fa-bookmark',
                callback: () => {
                    this._insertTableOfContent();
                },
            }, {
                category: 'Knowledge',
                name: _t('Item Kanban'),
                priority: 40,
                description: _t('Insert a Kanban view of article items'),
                fontawesome: 'fa-th-large',
                callback: () => {
                    const restoreSelection = preserveCursor(this.odooEditor.document);
                    const viewType = 'kanban';
                    this._openEmbeddedViewDialog(viewType, name => {
                        restoreSelection();
                        this._insertEmbeddedView('knowledge.knowledge_article_item_action', viewType, name, {
                            active_id: this.options.recordInfo.res_id,
                            default_parent_id: this.options.recordInfo.res_id,
                            default_icon: '📄',
                            default_is_article_item: true,
                        });
                    });
                }
            }, {
                category: 'Knowledge',
                name: _t('Item List'),
                priority: 50,
                description: _t('Insert a List view of article items'),
                fontawesome: 'fa-th-list',
                callback: () => {
                    const restoreSelection = preserveCursor(this.odooEditor.document);
                    const viewType = 'list';
                    this._openEmbeddedViewDialog(viewType, name => {
                        restoreSelection();
                        this._insertEmbeddedView('knowledge.knowledge_article_item_action', viewType, name, {
                            active_id: this.options.recordInfo.res_id,
                            default_parent_id: this.options.recordInfo.res_id,
                            default_icon: '📄',
                            default_is_article_item: true,
                        });
                    });
                }
            }, {
                category: 'Knowledge',
                name: _t('Index'),
                priority: 40,
                description: _t('Show the first level of nested articles.'),
                fontawesome: 'fa-list',
                callback: () => {
                    this._insertArticlesStructure(true);
                }
            }, {
                category: 'Knowledge',
                name: _t('Outline'),
                priority: 40,
                description: _t('Show all nested articles.'),
                fontawesome: 'fa-list',
                callback: () => {
                    this._insertArticlesStructure(false);
                }
            });
        }
        return {...options, commands, categories};
    },
    /**
     * Notify @see FieldHtmlInjector that behaviors need to be injected
     * @see KnowledgeBehavior
     *
     * @param {Element} anchor
     * @param {Object} props
     */
    _notifyNewBehavior(anchor, props=null) {
        const behaviorsData = [];
        const type = Array.from(anchor.classList).find(className => className.startsWith('o_knowledge_behavior_type_'));
        if (type) {
            behaviorsData.push({
                anchor: anchor,
                behaviorType: type,
                setCursor: true,
                props: props || {},
            });
        }
        this.$editable.trigger('refresh_behaviors', { behaviorsData: behaviorsData});
    },
    /**
     * Insert a /toc block (table of content)
     */
    _insertTableOfContent: function () {
        const tableOfContentBlock = $(QWeb.render('knowledge.abstract_behavior', {
            behaviorType: "o_knowledge_behavior_type_toc",
        }))[0];
        const [container] = this.odooEditor.execCommand('insert', tableOfContentBlock);
        this._notifyNewBehavior(container);
    },
    /**
     * Insert a /structure block.
     * It will list all the articles that are direct children of this one.
     * @param {boolean} childrenOnly
     */
    _insertArticlesStructure: function (childrenOnly) {
        const articlesStructureBlock = $(QWeb.render('knowledge.articles_structure_wrapper', {
            childrenOnly: childrenOnly
        }))[0];
        const [container] = this.odooEditor.execCommand('insert', articlesStructureBlock);
        this._notifyNewBehavior(container);
    },
    /**
     * Insert a /template block
     */
    _insertTemplate() {
        const templateBlock = $(QWeb.render('knowledge.abstract_behavior', {
            behaviorType: "o_knowledge_behavior_type_template",
        }))[0];
        const [container] = this.odooEditor.execCommand('insert', templateBlock);
        this._notifyNewBehavior(container);
    },
    /**
     * Insert a /article block (through a dialog)
     */
    _insertArticleLink: function () {
        const restoreSelection = preserveCursor(this.odooEditor.document);
        const dialog = new KnowledgeArticleLinkModal(this, {});
        dialog.on('save', this, article => {
            if (article) {
                const articleLinkBlock = $(QWeb.render('knowledge.wysiwyg_article_link', {
                    href: '/knowledge/article/' + article.id,
                    data: JSON.stringify({
                        article_id: article.id,
                        display_name: article.display_name,
                    }),
                }))[0];
                dialog.close();
                restoreSelection();
                const [anchor] = this.odooEditor.execCommand('insert', articleLinkBlock);
                this._notifyNewBehavior(anchor);
            }
        });
        dialog.on('closed', this, () => {
            restoreSelection();
        });
        dialog.open();
    },
    /**
     * Inserts a view in the editor
     * @param {String} actWindowId - Act window id of the action
     * @param {String} viewType - View type
     * @param {String} name - Name
     * @param {Object} context - Context
     */
    _insertEmbeddedView: async function (actWindowId, viewType, name, context={}) {
        const restoreSelection = preserveCursor(this.odooEditor.document);
        restoreSelection();
        context.knowledge_embedded_view_framework = 'owl';
        const embeddedViewBlock = $(await this._rpc({
            model: 'knowledge.article',
            method: 'render_embedded_view',
            args: [[this.options.recordInfo.res_id], actWindowId, viewType, name, context],
        }))[0];
        const [container] = this.odooEditor.execCommand('insert', embeddedViewBlock);
        this._notifyNewBehavior(container);
    },
    /**
     * Notify the @see FieldHtmlInjector when a /file block is inserted from a
     * @see MediaDialog
     *
     * @private
     * @override
     */
    _onMediaDialogSave(params, element) {
        if (element.classList.contains('o_is_knowledge_file')) {
            params.restoreSelection();
            element.classList.remove('o_is_knowledge_file');
            element.classList.add('o_image');
            const extension = (element.title && element.title.split('.').pop()) || element.dataset.mimetype;
            const fileBlock = $(QWeb.render('knowledge.abstract_behavior', {
                behaviorType: "o_knowledge_behavior_type_file",
            }))[0];
            const [container] = this.odooEditor.execCommand('insert', fileBlock);
            this._notifyNewBehavior(container, {
                fileName: element.title,
                fileImage: element.outerHTML,
                fileExtension: extension,
            });
            // need to set cursor (anchor.sibling)
        } else {
            return this._super(...arguments);
        }
    },
    /**
     * Inserts the dialog allowing the user to specify name for the embedded view.
     * @param {String} viewType
     * @param {Function} save
     */
    _openEmbeddedViewDialog: function (viewType, save) {
        // TODO: remove the wrapper when the wysiwyg is converted to owl.
        const dialog = new ComponentWrapper(this, PromptEmbeddedViewNameDialogWrapper, {
            isNew: true,
            viewType: viewType,
            save: save
        });
        dialog.mount(document.body);
    },
});
