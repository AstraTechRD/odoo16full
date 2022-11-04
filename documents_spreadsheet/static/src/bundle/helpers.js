/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { base64ToJson } from "@spreadsheet_edition/bundle/helpers";

const Model = spreadsheet.Model;

/**
 * Takes a template id as input, will convert the formulas
 * from relative to absolute in a way that they can be used to create a sheet.
 *
 * @param {Function} rpc
 * @param {number} templateId
 * @returns {Promise<Object>} spreadsheetData
 */
export async function getDataFromTemplate(env, orm, templateId) {
    let [{ data }] = await orm.read("spreadsheet.template", [templateId], ["data"]);
    data = base64ToJson(data);

    const model = new Model(migrate(data), {
        dataSources: new DataSources(orm),
    });
    await model.config.dataSources.waitForAllLoaded();
    const proms = [];
    for (const pivotId of model.getters.getPivotIds()) {
        proms.push(model.getters.getPivotDataSource(pivotId).prepareForTemplateGeneration());
    }
    await Promise.all(proms);
    model.dispatch("CONVERT_PIVOT_FROM_TEMPLATE");
    return model.exportData();
}
