/** @odoo-module */

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import {
    patchWithCleanup,
    click,
    getFixture,
    makeDeferred,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "./webclient_helpers";
import { SpreadsheetAction } from "../../src/bundle/actions/spreadsheet_action";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * Get a webclient with a list view.
 * The webclient is already configured to work with spreadsheet (env, registries, ...)
 *
 * @param {Object} params
 * @param {string} [params.model] Model name of the list
 * @param {Object} [params.serverData] Data to be injected in the mock server
 * @param {Function} [params.mockRPC] Mock rpc function
 * @param {object[]} [params.orderBy] orderBy argument
 * @returns {Promise<object>} Webclient
 */
export async function spawnListViewForSpreadsheet(params = {}) {
    const { model, serverData, mockRPC } = params;
    await prepareWebClientForSpreadsheet();
    const webClient = await createWebClient({
        serverData: serverData || getBasicServerData(),
        mockRPC,
    });

    await doAction(webClient, {
        name: "Partners",
        res_model: model || "partner",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
    });

    /** sort the view by field */
    const target = getFixture();
    for (let order of params.orderBy || []) {
        const selector = `thead th.o_column_sortable[data-name='${order.name}']`;
        await click(target.querySelector(selector));
        if (order.asc === false) {
            await click(target.querySelector(selector));
        }
    }
    return webClient;
}

/**
 * Create a spreadsheet model from a List controller
 *
 * @param {object} params
 * @param {string} [params.model] Model name of the list
 * @param {object} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @param {object[]} [params.orderBy] orderBy argument
 * @param {number} [params.linesNumber]
 *
 * @returns {Promise<{model: Model, webClient: object, env: object}>}
 */
export async function createSpreadsheetFromListView(params = {}) {
    const def = makeDeferred();
    let spreadsheetAction = {};
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            this._super();
            owl.onMounted(() => {
                spreadsheetAction = this;
                def.resolve();
            });
        },
    });
    const webClient = await spawnListViewForSpreadsheet({
        model: params.model,
        serverData: params.serverData,
        mockRPC: params.mockRPC,
        orderBy: params.orderBy,
    });
    const target = getFixture();
    /** Put the current list in a new spreadsheet */
    await click(target.querySelector(".o_favorite_menu button"));
    await click(target.querySelector(".o_insert_list_spreadsheet_menu"));
    /** @type {HTMLInputElement} */
    const input = target.querySelector(`.o-sp-dialog-meta-threshold-input`);
    input.value = params.linesNumber ? params.linesNumber.toString() : "10";
    await triggerEvent(input, null, "input");
    await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
    await def;
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataSourcesLoaded(model);
    return {
        webClient,
        model,
        env: getSpreadsheetActionEnv(spreadsheetAction),
    };
}
