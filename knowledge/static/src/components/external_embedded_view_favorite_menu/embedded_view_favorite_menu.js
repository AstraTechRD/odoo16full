/** @odoo-module */

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { supportedEmbeddedViews } from "@knowledge/components/external_embedded_view_insertion/views_renderers_patches";

const { Component } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

export class InsertEmbeddedViewMenu extends Component {
    _onInsertEmbeddedViewInArticle () {
        this.env.searchModel.trigger('insert-embedded-view');
    }
    _onInsertViewLinkInArticle () {
        this.env.searchModel.trigger('insert-view-link');
    }
}

InsertEmbeddedViewMenu.props = {};
InsertEmbeddedViewMenu.template = 'knowledge.InsertEmbeddedViewMenu';
InsertEmbeddedViewMenu.components = { DropdownItem };

favoriteMenuRegistry.add(
    'insert-embedded-view-menu',
    {
        Component: InsertEmbeddedViewMenu,
        groupNumber: 1, // arbitrary, to rethink later.
        isDisplayed: (env) => {
            // only support act_window with an id for now, but act_window
            // object could potentially be used too (rework backend API to insert
            // views in articles)
            return env.config.actionId && !env.searchModel._context.knowledge_embedded_view_framework &&
                supportedEmbeddedViews.has(env.config.viewType);
        },
    },
    { sequence: 1 } // arbitrary, to rethink later.
);
