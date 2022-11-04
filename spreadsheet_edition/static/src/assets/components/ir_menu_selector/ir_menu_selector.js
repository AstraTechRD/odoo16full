/** @odoo-module */

import { ComponentAdapter } from "web.OwlCompatibility";
import { Dialog } from "@web/core/dialog/dialog";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { StandaloneMany2OneField } from "../../widgets/standalone_many2one_field";

const { Component, onMounted, useState, useExternalListener, useEffect } = owl;

export class MenuSelectorWidgetAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.env = Component.env;
        onMounted(() => {
            this.widget.$el.addClass(this.props.class);
        });
        useEffect(() => {
            if(this.props.autoFocus){
                this.widget.getFocusableElement().focus();
            }
        }, () => [this.props.autofocus, this.widget.getFocusableElement()]);
    }

    _trigger_up(ev) {
        if (ev.name === "value-changed") {
            const { value } = ev.data;
            return this.props.onValueChanged(value);
        }
        super._trigger_up(ev);
    }

    /**
     * @override
     */
    async updateWidget(nextProps) {
        if(nextProps.menuId !== this.props.menuId){
            this.widget.updateWidgetValue(nextProps.menuId);
        }
    }

    renderWidget() {}

    /**
     * @override
     */
    get widgetArgs() {
        const domain = [
            ["action", "!=", false],
            ["id", "in", this.props.availableMenuIds],
        ]
        const attrs = {
            placeholder: this.env._t("Select a menu..."),
            string: this.env._t("Menu Items"),
        };
        return ["ir.ui.menu", this.props.menuId, domain, attrs];
    }
}

export class IrMenuSelector extends Component {
    setup() {
        this.StandaloneMany2OneField = StandaloneMany2OneField;
        this.menus = useService("menu");
    }

    get availableMenuIds() {
        return this.menus.getAll()
            .map((menu) => menu.id)
            .filter((menuId) => menuId !== "root");
    }
}
IrMenuSelector.components = { MenuSelectorWidgetAdapter };
IrMenuSelector.template = "spreadsheet_edition.IrMenuSelector";

export class IrMenuSelectorDialog extends Component {
    setup() {
        this.selectedMenu = useState({
            id: undefined,
        });
        // Clicking anywhere will close the link editor menu. It should be
        // prevented otherwise the chain of event would be broken.
        // A solution would be to listen all clicks coming from this dialog and stop
        // their propagation.
        // However, the autocomplete dropdown of the Many2OneField widget is *not*
        // a child of this component. It's actually a direct child of "body" ¯\_(ツ)_/¯
        // The following external listener handles this.
        useExternalListener(document.body, "click", (ev) => ev.stopPropagation());
    }
    _onConfirm() {
        this.props.onMenuSelected(this.selectedMenu.id);
    }
    _onValueChanged(value) {
        this.selectedMenu.id = value;
    }
}
IrMenuSelectorDialog.components = { Dialog, IrMenuSelector };
IrMenuSelectorDialog.title = _lt("Select an Odoo menu to link in your spreadsheet");
IrMenuSelectorDialog.template = "spreadsheet_edition.IrMenuSelectorDialog";
