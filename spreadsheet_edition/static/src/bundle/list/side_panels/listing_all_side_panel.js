/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ListingDetailsSidePanel } from "./listing_details_side_panel";

const { Component } = owl;

export default class ListingAllSidePanel extends Component {
    constructor() {
        super(...arguments);
        this.getters = this.env.model.getters;
    }

    selectListing(listId) {
        this.env.model.dispatch("SELECT_ODOO_LIST", { listId });
    }

    resetListingSelection() {
        this.env.model.dispatch("SELECT_ODOO_LIST");
    }

    delete(listId) {
        this.env.askConfirmation(_t("Are you sure you want to delete this list ?"), () => {
            this.env.model.dispatch("REMOVE_ODOO_LIST", { listId });
            this.props.onCloseSidePanel();
        });
    }
}
ListingAllSidePanel.template = "spreadsheet_edition.ListingAllSidePanel";
ListingAllSidePanel.components = { ListingDetailsSidePanel };
