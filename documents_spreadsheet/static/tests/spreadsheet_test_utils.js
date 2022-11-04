/** @odoo-module */

import { jsonToBase64 } from "@spreadsheet_edition/bundle/helpers";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { SpreadsheetTemplateAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_template/spreadsheet_template_action";
import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "./utils/webclient_helpers";

/**
 * @typedef {import("@spreadsheet/../tests/utils/data").ServerData} ServerData
 */

/**
 * @typedef {object} SpreadsheetTestParams
 * @property {object} [webClient] Webclient already configured
 * @property {number} [spreadsheetId] Id of the spreadsheet
 * @property {ServerData} [serverData] Data to be injected in the mock server
 * @property {Function} [mockRPC] Mock rpc function
 */

/**
 * Open a spreadsheet action
 *
 * @param {string} actionTag Action tag ("action_open_spreadsheet" or "action_open_template")
 * @param {SpreadsheetTestParams} params
 */
async function createSpreadsheetAction(actionTag, params) {
    const SpreadsheetActionComponent =
        actionTag === "action_open_spreadsheet" ? SpreadsheetAction : SpreadsheetTemplateAction;
    let { webClient } = params;
    /** @type {any} */
    let spreadsheetAction;
    patchWithCleanup(SpreadsheetActionComponent.prototype, {
        setup() {
            this._super();
            spreadsheetAction = this;
        },
    });
    if (!webClient) {
        await prepareWebClientForSpreadsheet();
        webClient = await createWebClient({
            serverData: params.serverData || getBasicServerData(),
            mockRPC: params.mockRPC,
            legacyParams: {
                withLegacyMockServer: true,
            },
        });
    }

    await doAction(
        webClient,
        {
            type: "ir.actions.client",
            tag: actionTag,
            params: {
                spreadsheet_id: params.spreadsheetId,
            },
        },
        { clearBreadcrumbs: true } // Sometimes in test defining custom action, Odoo opens on the action instead of opening on root
    );
    return {
        webClient,
        model: getSpreadsheetActionModel(spreadsheetAction),
        env: getSpreadsheetActionEnv(spreadsheetAction),
        transportService: spreadsheetAction.transportService,
    };
}

/**
 * Create an empty spreadsheet
 *
 * @param {SpreadsheetTestParams} params
 */
export async function createSpreadsheet(params = {}) {
    if (!params.serverData) {
        params.serverData = getBasicServerData();
    }
    if (!params.spreadsheetId) {
        const documents = params.serverData.models["documents.document"].records;
        const spreadsheetId = Math.max(...documents.map((d) => d.id)) + 1;
        documents.push({
            id: spreadsheetId,
            name: UNTITLED_SPREADSHEET_NAME,
            raw: "{}",
        });
        params = { ...params, spreadsheetId };
    }
    return createSpreadsheetAction("action_open_spreadsheet", params);
}

/**
 * Create a spreadsheet template
 *
 * @param {SpreadsheetTestParams} params
 */
export async function createSpreadsheetTemplate(params = {}) {
    if (!params.serverData) {
        params.serverData = getBasicServerData();
    }
    if (!params.spreadsheetId) {
        const templates = params.serverData.models["spreadsheet.template"].records;
        const spreadsheetId = Math.max(...templates.map((d) => d.id)) + 1;
        templates.push({
            id: spreadsheetId,
            name: "test template",
            data: jsonToBase64({}),
        });
        params = { ...params, spreadsheetId };
    }
    return createSpreadsheetAction("action_open_template", params);
}
