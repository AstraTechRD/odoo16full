/** @odoo-module */

import { busService } from '@bus/services/bus_service';
import { multiTabService } from "@bus/multi_tab_service";

import { InsertListSpreadsheetMenu } from "@spreadsheet_edition/assets/list_view/insert_list_spreadsheet_menu_owl";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { loadJS } from "@web/core/assets";
import { dialogService } from "@web/core/dialog/dialog_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { viewService } from "@web/views/view_service";
import { makeFakeSpreadsheetService } from "@spreadsheet_edition/../tests/utils/collaborative_helpers";

const serviceRegistry = registry.category("services");

export async function prepareWebClientForSpreadsheet() {
    await loadJS("/web/static/lib/Chart/Chart.js");
    await loadJS("/spreadsheet/static/lib/chartjs-gauge/chartjs-gauge.js");
    serviceRegistry.add("spreadsheet_collaborative", makeFakeSpreadsheetService(), { force: true });
    serviceRegistry.add(
        "user",
        makeFakeUserService(() => true),
        { force: true }
    );
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("dialog", dialogService);
    serviceRegistry.add("ui", uiService);
    serviceRegistry.add("view", viewService, { force: true }); // #action-serv-leg-compat-js-class
    serviceRegistry.add("orm", ormService, { force: true }); // #action-serv-leg-compat-js-class
    serviceRegistry.add("bus_service", busService);
    serviceRegistry.add('multi_tab', multiTabService);
    registry.category("favoriteMenu").add(
        "insert-list-spreadsheet-menu",
        {
            Component: InsertListSpreadsheetMenu,
            groupNumber: 4,
            isDisplayed: ({ config, isSmall }) =>
                !isSmall &&
                config.actionType === "ir.actions.act_window" &&
                config.viewType === "list",
        },
        { sequence: 5 }
    );
}

/**
 * Return the odoo spreadsheet component
 * @param {*} actionManager
 * @returns {Component}
 */
export function getSpreadsheetComponent(actionManager) {
    return actionManager.spreadsheet;
}

/**
 * Return the o-spreadsheet component
 * @param {*} actionManager
 * @returns {Component}
 */
export function getOSpreadsheetComponent(actionManager) {
    return getSpreadsheetComponent(actionManager).spreadsheet;
}

/**
 * Return the o-spreadsheet Model
 */
export function getSpreadsheetActionModel(actionManager) {
    return getOSpreadsheetComponent(actionManager).model;
}

export function getSpreadsheetActionTransportService(actionManager) {
    return actionManager.transportService;
}

export function getSpreadsheetActionEnv(actionManager) {
    const model = getSpreadsheetActionModel(actionManager);
    const component = getSpreadsheetComponent(actionManager);
    const oComponent = getOSpreadsheetComponent(actionManager);
    return Object.assign(Object.create(component.env), {
        model,
        openSidePanel: oComponent.openSidePanel.bind(oComponent),
    });
}
