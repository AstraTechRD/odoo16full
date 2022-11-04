/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { ComponentAdapter } from "web.OwlCompatibility";
import { MenuItem } from "web_studio.EditMenu";

const { Component, onMounted, onPatched, onWillUpdateProps, xml } = owl;

class EditMenuItemAdapter extends ComponentAdapter {
    constructor(props) {
        props.Component = MenuItem;
        super(...arguments);
    }

    setup() {
        super.setup();
        this.menus = useService("menu");
        this.env = Component.env;
        onMounted(() => {
            if (this.props.keepOpen) {
                this.widget.editMenu(this.props.scrollToBottom);
            }
        });
    }

    get currentMenuId() {
        return this.menus.getCurrentApp().id;
    }

    get legacyMenuData() {
        return this.menus.getMenuAsTree("root");
    }

    get widgetArgs() {
        return [this.legacyMenuData, this.currentMenuId];
    }
    _trigger_up(ev) {
        if (ev.name === "reload_menu_data") {
            this.props.reloadMenuData(ev);
        }
        super._trigger_up(...arguments);
    }

    updateWidget() {}
    renderWidget() {}
}

// why a high order component ?
// - support navbar re-rendering without having to fiddle too much in
// the legacy widget's code
// - allow to support the keepopen, and autoscroll features (yet to come)
export class EditMenuItem extends Component {
    setup() {
        this.menus = useService("menu");
        this.localId = 0;
        this.editMenuParams = {};

        onWillUpdateProps(() => {
            this.localId++;
        });
        onPatched(() => {
            this.editMenuParams = {};
        });
    }
    reloadMenuData(ev) {
        const { keep_open, scroll_to_bottom } = ev.data;
        this.editMenuParams = { keepOpen: keep_open, scrollToBottom: scroll_to_bottom };
        this.menus.reload();
    }
}
EditMenuItem.components = { EditMenuItemAdapter };
EditMenuItem.template = xml`
  <t>
    <div t-if="!menus.getCurrentApp()"/>
    <EditMenuItemAdapter t-else="" t-key="localId" t-props="editMenuParams" reloadMenuData.bind="reloadMenuData" />
  </t>
`;
