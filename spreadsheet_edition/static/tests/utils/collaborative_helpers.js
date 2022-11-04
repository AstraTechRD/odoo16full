/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import MockSpreadsheetCollaborativeChannel from "./mock_spreadsheet_collaborative_channel";
import { ormService } from "@web/core/orm_service";
import { uiService } from "@web/core/ui/ui_service";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { setupDataSourceEvaluation } from "@spreadsheet/../tests/utils/model";
import { spreadsheetCollaborativeService } from "@spreadsheet_edition/bundle/o_spreadsheet/collaborative/spreadsheet_collaborative_service";

const { Model } = spreadsheet;
const serviceRegistry = registry.category("services");

export function makeFakeSpreadsheetService() {
    return {
        ...spreadsheetCollaborativeService,
        start() {
            const fakeSpreadsheetService = spreadsheetCollaborativeService.start(...arguments);
            fakeSpreadsheetService.getCollaborativeChannel = () =>
                new MockSpreadsheetCollaborativeChannel();
            return fakeSpreadsheetService;
        },
    };
}


export function joinSession(spreadsheetChannel, client) {
    spreadsheetChannel.broadcast({
        type: "CLIENT_JOINED",
        client: {
            position: {
                sheetId: "1",
                col: 1,
                row: 1,
            },
            name: "Raoul Grosbedon",
            ...client,
        },
    });
}

export function leaveSession(spreadsheetChannel, clientId) {
    spreadsheetChannel.broadcast({
        type: "CLIENT_LEFT",
        clientId,
    });
}

/**
 * Setup a realtime collaborative test environment, with the given data
 */
export async function setupCollaborativeEnv(serverData) {
    serviceRegistry.add("ui", uiService);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("localization", makeFakeLocalizationService());
    const env = await makeTestEnv({ serverData });

    const network = new MockSpreadsheetCollaborativeChannel();
    const model = new Model();
    const alice = new Model(model.exportData(), {
        dataSources: new DataSources(env.services.orm),
        evalContext: { env },
        transportService: network,
        client: { id: "alice", name: "Alice" },
    });
    const bob = new Model(model.exportData(), {
        dataSources: new DataSources(env.services.orm),
        evalContext: { env },
        transportService: network,
        client: { id: "bob", name: "Bob" },
    });
    const charlie = new Model(model.exportData(), {
        dataSources: new DataSources(env.services.orm),
        evalContext: { env },
        transportService: network,
        client: { id: "charlie", name: "Charlie" },
    });
    setupDataSourceEvaluation(alice);
    setupDataSourceEvaluation(bob);
    setupDataSourceEvaluation(charlie);
    return { network, alice, bob, charlie, rpc: env.services.rpc };
}

QUnit.assert.spreadsheetIsSynchronized = function (users, callback, expected) {
    for (const user of users) {
        const actual = callback(user);
        if (!QUnit.equiv(actual, expected)) {
            const userName = user.getters.getClient().name;
            return this.pushResult({
                result: false,
                actual,
                expected,
                message: `${userName} does not have the expected value`,
            });
        }
    }
    this.pushResult({ result: true });
};
