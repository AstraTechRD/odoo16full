/** @odoo-module */

import NewModel from "web_studio.NewModel";
import { ComponentAdapter } from "web.OwlCompatibility";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillUpdateProps, xml } = owl;

class NewModelItemAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.env = Component.env;
    }
    _trigger_up(ev) {
        if (ev.name === "reload_menu_data") {
            this.props.reloadMenuData(ev);
        } else if (ev.name === "menu_clicked") {
            this.props.editNewModel(ev);
        }
        super._trigger_up(...arguments);
    }
}

export class NewModelItem extends Component {
    setup() {
        this.NewModel = NewModel;
        this.menus = useService("menu");
        this.studio = useService("studio");
        this.action = useService("action");
        this.localId = 0;
        onWillUpdateProps(() => this.localId++);
    }

    async editNewModel(ev) {
        const { action_id, options } = ev.detail;
        const action = await this.action.loadAction(action_id);
        this.studio.setParams({ action, viewType: (options && options.viewType) || "form" });
    }
}
NewModelItem.template = xml`
  <t>
    <t t-set="currentApp" t-value="menus.getCurrentApp()" />
    <NewModelItemAdapter t-if="currentApp"
       Component="NewModel.NewModelItem"
       widgetArgs="[currentApp and currentApp.id]"
       t-key="localId"
       reloadMenuData.bind= "() => { this.menus.reload(); }"
       editNewModel.bind="editNewModel" />
    <div t-else="" />
  </t>
`;
NewModelItem.components = { NewModelItemAdapter };
