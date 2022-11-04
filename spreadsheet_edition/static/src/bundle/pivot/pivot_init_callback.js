/** @odoo-module **/
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import PivotDataSource from "@spreadsheet/pivot/pivot_data_source";

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

export function insertPivot(pivotData) {
    const definition = {
        metaData: {
            colGroupBys: [...pivotData.metaData.fullColGroupBys],
            rowGroupBys: [...pivotData.metaData.fullRowGroupBys],
            activeMeasures: [...pivotData.metaData.activeMeasures],
            resModel: pivotData.metaData.resModel,
            fields: pivotData.metaData.fields,
            sortedColumn: pivotData.metaData.sortedColumn,
        },
        searchParams: { ...pivotData.searchParams },
        name: pivotData.name,
    };
    return async (model) => {
        const dataSourceId = uuidGenerator.uuidv4();
        model.config.dataSources.add(dataSourceId, PivotDataSource, definition);
        await model.config.dataSources.load(dataSourceId);
        const pivotDataSource = model.config.dataSources.get(dataSourceId);
        // Add an empty sheet in the case of an existing spreadsheet.
        if (!this.isEmptySpreadsheet) {
            const sheetId = uuidGenerator.uuidv4();
            const sheetIdFrom = model.getters.getActiveSheetId();
            model.dispatch("CREATE_SHEET", {
                sheetId,
                position: model.getters.getSheetIds().length,
            });
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        }
        const structure = pivotDataSource.getTableStructure();
        const table = structure.export();
        const sheetId = model.getters.getActiveSheetId();

        const defWithoutFields = JSON.parse(JSON.stringify(definition));
        defWithoutFields.metaData.fields = undefined;
        model.dispatch("INSERT_PIVOT", {
            sheetId,
            col: 0,
            row: 0,
            table,
            id: model.getters.getNextPivotId(),
            dataSourceId,
            definition: defWithoutFields,
        });
        const columns = [];
        for (let col = 0; col <= table.cols[table.cols.length - 1].length; col++) {
            columns.push(col);
        }
        model.dispatch("AUTORESIZE_COLUMNS", { sheetId, cols: columns });
    };
}
