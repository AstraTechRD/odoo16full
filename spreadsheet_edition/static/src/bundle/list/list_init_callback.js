/** @odoo-module **/
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import ListDataSource from "@spreadsheet/list/list_data_source";

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

/**
 * Get the function that have to be executed to insert the given list in the
 * given spreadsheet. The returned function has to be called with the model
 * of the spreadsheet and the dataSource of this list
 *
 * @private
 *
 * @param {import("@spreadsheet/list/plugins/list_core_plugin").SpreadsheetList} list
 * @param {object} param
 * @param {number} param.threshold
 * @param {object} param.fields fields coming from list_model
 * @param {string} param.name Name of the list
 *
 * @returns {function}
 */
export function insertList({ list, threshold, fields, name }) {
    const definition = {
        metaData: {
            resModel: list.model,
            columns: list.columns.map((column) => column.name),
            fields,
        },
        searchParams: {
            domain: list.domain,
            context: list.context,
            orderBy: list.orderBy,
        },
        name,
    };
    return async (model) => {
        const dataSourceId = uuidGenerator.uuidv4();
        model.config.dataSources.add(dataSourceId, ListDataSource, {
            ...definition,
            limit: threshold,
        });
        await model.config.dataSources.load(dataSourceId);
        if (!this.isEmptySpreadsheet) {
            const sheetId = uuidGenerator.uuidv4();
            const sheetIdFrom = model.getters.getActiveSheetId();
            model.dispatch("CREATE_SHEET", {
                sheetId,
                position: model.getters.getSheetIds().length,
            });
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        }
        const defWithoutFields = JSON.parse(JSON.stringify(definition));
        defWithoutFields.metaData.fields = undefined;
        const sheetId = model.getters.getActiveSheetId();
        model.dispatch("INSERT_ODOO_LIST", {
            sheetId,
            col: 0,
            row: 0,
            id: model.getters.getNextListId(),
            definition: defWithoutFields,
            dataSourceId,
            linesNumber: threshold,
            columns: list.columns,
        });
        const columns = [];
        for (let col = 0; col < list.columns.length; col++) {
            columns.push(col);
        }
        model.dispatch("AUTORESIZE_COLUMNS", { sheetId, cols: columns });
    };
}
