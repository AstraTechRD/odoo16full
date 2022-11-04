/** @odoo-module */

import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { makeContext } from "@web/core/context";
import { useService } from "@web/core/utils/hooks";

const { useEffect } = owl;


/**
 * Clickable "link" to access a view from an article with custom facets (only
 * usable in Odoo)
 */
export class ViewLinkBehavior extends AbstractBehavior {
    setup () {
        super.setup();
        this.actionService = useService('action');
        useEffect(() => {
            const type = this.props.readonly ? 'click' : 'dblclick';
            /**
             * @param {Event} event
             */
            const onLinkClick = event => {
                this.openViewLink(event);
            };
            this.props.anchor.addEventListener(type, onLinkClick);
            return () => {
                this.props.anchor.removeEventListener(type, onLinkClick);
            };
        });
    }

    /**
     * @param {Event} event
     */
    async openViewLink (event) {
        const action = await this.actionService.loadAction(
            this.props.act_window,
            makeContext([this.props.context])
        );
        if (action.type !== "ir.actions.act_window") {
            throw new Error('Can not open the view: The action is not an "ir.actions.act_window"');
        }
        action.globalState = {
            searchModel: this.props.context.knowledge_search_model_state
        };
        this.actionService.doAction(action, {
            viewType: this.props.view_type
        });
    }
}

ViewLinkBehavior.template = "knowledge.ViewLinkBehavior";
ViewLinkBehavior.components = {};
ViewLinkBehavior.props = {
    ...AbstractBehavior.props,
    act_window: { type: Object },
    context: { type: Object },
    name: { type: String },
    view_type: { type: String }
};
