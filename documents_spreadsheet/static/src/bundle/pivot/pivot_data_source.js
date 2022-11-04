/** @odoo-module */

import PivotDataSource from "@spreadsheet/pivot/pivot_data_source";
import { patch } from "@web/core/utils/patch";

patch(PivotDataSource.prototype, "documents_spreadsheet_templates_data_source", {
    /**
     * @param {string} fieldName
     */
    getPossibleValuesForGroupBy(fieldName) {
        this._assertDataIsLoaded();
        return this._model.getPossibleValuesForGroupBy(fieldName);
    },
});
