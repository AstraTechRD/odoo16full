/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";
import spreadsheet, { initCallbackRegistry } from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { buildIrMenuIdLink, buildViewLink, buildIrMenuXmlLink } from "@spreadsheet/ir_ui_menu/odoo_menu_link_cell"
import { IrMenuSelectorDialog } from "@spreadsheet_edition/assets/components/ir_menu_selector/ir_menu_selector";

const { markdownLink } = spreadsheet.helpers;
const { linkMenuRegistry } = spreadsheet.registries;

/**
 * Helper to get the function to be called when the spreadsheet is opened
 * in order to insert the link.
 * @param {import("@spreadsheet/ir_ui_menu/odoo_menu_link_cell").ViewLinkDescription} actionToLink
 * @returns Function to call
 */
 function insertLink(actionToLink) {
    return (model) => {
        if (!this.isEmptySpreadsheet) {
            const sheetId = model.uuidGenerator.uuidv4();
            const sheetIdFrom = model.getters.getActiveSheetId();
            model.dispatch("CREATE_SHEET", {
                sheetId,
                position: model.getters.getSheetIds().length,
            });
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        }
        const viewLink = buildViewLink(actionToLink);
        model.dispatch("UPDATE_CELL", {
            sheetId: model.getters.getActiveSheetId(),
            content: markdownLink(actionToLink.name, viewLink),
            col: 0,
            row: 0,
        });
    };
}

initCallbackRegistry.add("insertLink", insertLink);

linkMenuRegistry.add("odooMenu", {
    name: _lt("Link an Odoo menu"),
    sequence: 20,
    action: async (env) => {
        return new Promise((resolve) => {
            const closeDialog = env.services.dialog.add(IrMenuSelectorDialog, {
                onMenuSelected: (menuId) => {
                    closeDialog();
                    const menu = env.services.menu.getMenu(menuId);
                    const xmlId = menu && menu.xmlid;
                    const url = xmlId ? buildIrMenuXmlLink(xmlId) : buildIrMenuIdLink(menuId);
                    const name = menu.name;
                    const link = { url, label: name };
                    resolve({
                        link,
                        isUrlEditable: false,
                        urlRepresentation: name,
                    });
                },
            });
        });
    },
});
