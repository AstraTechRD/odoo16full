/** @odoo-module */

import { HtmlField } from "@web_editor/js/backend/html_field";
import { KnowledgePlugin } from "@knowledge/js/knowledge_plugin";
import { patch } from "@web/core/utils/patch";
import { templates } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";

// Behaviors:

import { ArticleBehavior } from "@knowledge/components/behaviors/article_behavior/article_behavior";
import { ArticlesStructureBehavior } from "@knowledge/components/behaviors/articles_structure_behavior/articles_structure_behavior";
import { FileBehavior } from "@knowledge/components/behaviors/file_behavior/file_behavior";
import { EmbeddedViewBehavior } from "@knowledge/components/behaviors/embedded_view_behavior/embedded_view_behavior";
import { TemplateBehavior } from "@knowledge/components/behaviors/template_behavior/template_behavior";
import { TableOfContentBehavior } from "@knowledge/components/behaviors/table_of_content_behavior/table_of_content_behavior";
import { ViewLinkBehavior } from "@knowledge/components/behaviors/view_link_behavior/view_link_behavior";

const {
    App,
    onMounted,
    onPatched,
    onWillDestroy,
    onWillUnmount,
} = owl;

const behaviorTypes = {
    o_knowledge_behavior_type_article: {
        Behavior: ArticleBehavior,
    },
    o_knowledge_behavior_type_file: {
        Behavior: FileBehavior,
    },
    o_knowledge_behavior_type_template: {
        Behavior: TemplateBehavior,
    },
    o_knowledge_behavior_type_toc: {
        Behavior: TableOfContentBehavior,
    },
    o_knowledge_behavior_type_articles_structure: {
        Behavior: ArticlesStructureBehavior
    },
    o_knowledge_behavior_type_embedded_view: {
        Behavior: EmbeddedViewBehavior
    },
    o_knowledge_behavior_type_view_link: {
        Behavior: ViewLinkBehavior
    },
};

const HtmlFieldPatch = {
    setup() {
        this._super(...arguments);
        this.behaviorAnchors = new Set();
        this.bindedDelayedRefreshBehaviors = this.delayedRefreshBehaviors.bind(this);
        this.uiService = useService('ui');
        onWillUnmount(() => {
            if (!this.props.readonly) {
                this._removeRefreshBehaviorsListeners();
            }
        });
        onMounted(() => {
            if (this.props.readonly) {
                this.updateBehaviors();
            }
        });
        onPatched(() => {
            this.updateBehaviors();
        });
        onWillDestroy(() => {
            for (const anchor of Array.from(this.behaviorAnchors)) {
                if (anchor.oKnowledgeBehavior) {
                    anchor.oKnowledgeBehavior.destroy();
                    delete anchor.oKnowledgeBehavior;
                }
            }
        });
    },
    /**
     * @returns {Object}
     */
    get behaviorTypes() {
        return behaviorTypes;
    },
    /**
     * @returns {HTMLElement}
     */
    get injectorEl() {
        if (this.props.readonly && this.readonlyElementRef.el) {
            return this.readonlyElementRef.el;
        } else if (this.wysiwyg && this.wysiwyg.$editable) {
            return this.wysiwyg.$editable[0];
        }
        return null;
    },
    /**
     * @returns {integer}
     */
    delayedRefreshBehaviors() {
        return window.setTimeout(this.updateBehaviors.bind(this));
    },
    /**
     * @override
     * @param {Widget} wysiwyg
     */
    async startWysiwyg(wysiwyg) {
        await this._super(...arguments);
        this._addRefreshBehaviorsListeners();
        await this.updateBehaviors();
    },
    /**
     * @param {Array[Object]} behaviorsData
     */
    async updateBehaviors(behaviorsData = [], target = null) {
        const injectorEl = target || this.injectorEl;
        if (!injectorEl) {
            return;
        }
        if (!behaviorsData.length) {
            this._scanFieldForBehaviors(behaviorsData, injectorEl);
        }
        for (const behaviorData of behaviorsData) {
            const anchor = behaviorData.anchor;
            if (!document.body.contains(anchor)) {
                // trying to mount components on nodes that were removed from
                // the dom => no need to continue
                // this is due to the fact that this function is asynchronous
                // but onPatched and onMounted are synchronous and do not
                // wait for their content to finish so the life cycle of
                // the component can continue during the execution of this function
                return;
            }
            const {Behavior} = this.behaviorTypes[behaviorData.behaviorType] || {};
            if (!Behavior) {
                return;
            }
            if (!anchor.oKnowledgeBehavior) {
                if (!this.props.readonly && this.wysiwyg && this.wysiwyg.odooEditor) {
                    this.wysiwyg.odooEditor.observerUnactive('injectBehavior');
                }
                // parse html to get all data-behavior-props content nodes
                const props = {
                    readonly: this.props.readonly,
                    anchor: anchor,
                    wysiwyg: this.wysiwyg,
                    ...behaviorData.props,
                    record: this.props.record
                };
                let behaviorProps = {};
                if (anchor.hasAttribute("data-behavior-props")) {
                    try {
                        behaviorProps = JSON.parse(anchor.dataset.behaviorProps);
                    } catch {}
                }
                for (const prop in behaviorProps) {
                    if (prop in Behavior.props) {
                        props[prop] = behaviorProps[prop];
                    }
                }
                const propNodes = anchor.querySelectorAll("[data-prop-name]");
                for (const node of propNodes) {
                    if (node.dataset.propName in Behavior.props) {
                        props[node.dataset.propName] = node.innerHTML;
                    }
                }
                anchor.replaceChildren();
                const config = (({env, dev, translatableAttributes, translateFn}) => {
                    return {env, dev, translatableAttributes, translateFn};
                })(this.__owl__.app);
                anchor.oKnowledgeBehavior = new App(Behavior, {
                    ...config,
                    templates: templates,
                    props,
                });
                await anchor.oKnowledgeBehavior.mount(anchor);
                if (!this.props.readonly && this.wysiwyg && this.wysiwyg.odooEditor) {
                    this.wysiwyg.odooEditor.idSet(anchor);
                    this.wysiwyg.odooEditor.observerActive('injectBehavior');
                    if (behaviorData.setCursor && anchor.oKnowledgeBehavior.root.component.setCursor) {
                        anchor.oKnowledgeBehavior.root.component.setCursor();
                    }
                    this.wysiwyg.odooEditor.historyStep();
                }
                await this.updateBehaviors([], anchor);
            }
        }
    },
    _addRefreshBehaviorsListeners() {
        if (this.wysiwyg.odooEditor) {
            this.wysiwyg.odooEditor.addEventListener('historyUndo', this.bindedDelayedRefreshBehaviors);
            this.wysiwyg.odooEditor.addEventListener('historyRedo', this.bindedDelayedRefreshBehaviors);
        }
        if (this.wysiwyg.$editable.length) {
            this.wysiwyg.$editable[0].addEventListener('paste', this.bindedDelayedRefreshBehaviors);
            this.wysiwyg.$editable[0].addEventListener('drop', this.bindedDelayedRefreshBehaviors);
            this.wysiwyg.$editable.on('refresh_behaviors', this._onRefreshBehaviors.bind(this));
        }
    },
    _onRefreshBehaviors(e, data = {}) {
        this.updateBehaviors("behaviorsData" in data ? data.behaviorsData : []);
    },
    _removeRefreshBehaviorsListeners() {
        if (this.wysiwyg.odooEditor) {
            this.wysiwyg.odooEditor.removeEventListener('historyUndo', this.bindedDelayedRefreshBehaviors);
            this.wysiwyg.odooEditor.removeEventListener('historyRedo', this.bindedDelayedRefreshBehaviors);
        }
        if (this.wysiwyg.$editable.length) {
            this.wysiwyg.$editable[0].removeEventListener('paste', this.bindedDelayedRefreshBehaviors);
            this.wysiwyg.$editable[0].removeEventListener('drop', this.bindedDelayedRefreshBehaviors);
            this.wysiwyg.$editable.off('refresh_behaviors');
        }
    },
    /**
     * @param {Array[Object]} behaviorsData
     * @param {HTMLElement} target
     */
    _scanFieldForBehaviors(behaviorsData, target) {
        const anchors = new Set();
        const types = new Set(Object.getOwnPropertyNames(this.behaviorTypes));
        const anchorNodes = target.querySelectorAll('.o_knowledge_behavior_anchor');
        const anchorNodesSet = new Set(anchorNodes);
        for (const anchorNode of anchorNodes) {
            const anchorSubNodes = anchorNode.querySelectorAll('.o_knowledge_behavior_anchor');
            for (const anchorSubNode of anchorSubNodes) {
                anchorNodesSet.delete(anchorSubNode);
            }
        }
        for (const anchor of Array.from(anchorNodesSet)) {
            const type = Array.from(anchor.classList).find(className => types.has(className));
            if (type) {
                behaviorsData.push({
                    anchor: anchor,
                    behaviorType: type,
                });
                anchors.add(anchor);
            }
        }
        // difference between the stored set and the computed one
        const differenceAnchors = new Set([...this.behaviorAnchors].filter(anchor => !anchors.has(anchor)));
        // remove obsolete behaviors
        differenceAnchors.forEach(anchor => {
            if (anchor.oKnowledgeBehavior) {
                anchor.oKnowledgeBehavior.destroy();
                delete anchor.oKnowledgeBehavior;
            }
        });
    },
};

const extractProps = HtmlField.extractProps;

HtmlField.extractProps = ({ attrs, field }) => {
    const props = extractProps({ attrs, field });
    props.wysiwygOptions.knowledgeCommands = attrs.options.knowledge_commands;
    props.wysiwygOptions.editorPlugins.push(KnowledgePlugin);
    return props;
};

patch(HtmlField.prototype, 'knowledge_html_field', HtmlFieldPatch);
