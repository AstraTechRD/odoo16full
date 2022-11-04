/** @odoo-module */

/**
 * Plugin for OdooEditor. Allow to remove temporary toolbars content which are
 * not destined to be stored in the field_html
 */
export class KnowledgePlugin {
    constructor ({ editor }) {
        this.editor = editor;
    }
    /**
     * @param {Element} editable
     */
    cleanForSave(editable) {
        for (const node of editable.querySelectorAll('.o_knowledge_behavior_anchor')) {
            if (node.oKnowledgeBehavior) {
                node.oKnowledgeBehavior.destroy();
                delete node.oKnowledgeBehavior;
            }

            const nodesToRemove = node.querySelectorAll('.o_knowledge_clean_for_save');
            for (const node of nodesToRemove) {
                node.remove();
            }
        }
    }
}
