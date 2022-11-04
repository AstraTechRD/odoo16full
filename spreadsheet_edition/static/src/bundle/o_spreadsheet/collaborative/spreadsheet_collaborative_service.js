/** @odoo-module */

import { registry } from "@web/core/registry";
import SpreadsheetCollaborativeChannel from "./spreadsheet_collaborative_channel";

export class SpreadsheetCollaborativeService {
    /**
     * Get a new collaborative channel for the given spreadsheet id
     * @param {Env} env Env of owl (Component.env)
     * @param {string} resModel model linked to the spreadsheet
     * @param {number} resId id of the spreadsheet
     */
    getCollaborativeChannel(env, resModel, resId) {
        return new SpreadsheetCollaborativeChannel(env, resModel, resId);
    }
}

/**
 * This service exposes a single instance of the above class.
 */
export const spreadsheetCollaborativeService = {
    dependencies: ['bus_service'],
    start(env, dependencies) {
        return new SpreadsheetCollaborativeService(env, dependencies);
    },
};

registry.category("services").add("spreadsheet_collaborative", spreadsheetCollaborativeService);
