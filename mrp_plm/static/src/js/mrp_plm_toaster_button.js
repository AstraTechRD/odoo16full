/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class PlmToasterButton extends Component {
    setup() {
        this.notification = useService("notification");
    }

    async onClick() {
        const message = "Note that a new version of this BOM is available.";
        this.notification.add(message);
    }
}

PlmToasterButton.template = "mrp_plm.ToasterButton"
PlmToasterButton.displayName = "MRP_PLM Toaster Button"

registry.category("view_widgets").add("plm_toaster_button", PlmToasterButton);

