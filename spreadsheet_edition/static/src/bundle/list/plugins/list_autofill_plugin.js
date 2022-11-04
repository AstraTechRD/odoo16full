/** @odoo-module */

import { _t } from "web.core";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { getFirstListFunction, getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";

const { astToFormula } = spreadsheet;

export default class ListAutofillPlugin extends spreadsheet.UIPlugin {
    // ---------------------------------------------------------------------
    // Getters
    // ---------------------------------------------------------------------

    /**
     * Get the next value to autofill of a list function
     *
     * @param {string} formula List formula
     * @param {boolean} isColumn True if autofill is LEFT/RIGHT, false otherwise
     * @param {number} increment number of steps
     *
     * @returns Autofilled value
     */
    getNextListValue(formula, isColumn, increment) {
        if (getNumberOfListFormulas(formula) !== 1) {
            return formula;
        }
        const { functionName, args } = getFirstListFunction(formula);
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(arg));
        const listId = evaluatedArgs[0];
        const columns = this.getters.getListDefinition(listId).columns;
        if (functionName === "ODOO.LIST") {
            const position = parseInt(evaluatedArgs[1], 10);
            const field = evaluatedArgs[2];
            if (isColumn) {
                /** Change the field */
                const index = columns.findIndex((col) => col === field) + increment;
                if (index < 0 || index >= columns.length) {
                    return "";
                }
                return this._getListFunction(listId, position, columns[index]);
            } else {
                /** Change the position */
                const nextPosition = position + increment;
                if (nextPosition === 0) {
                    return this._getListHeaderFunction(listId, field);
                }
                if (nextPosition < 0) {
                    return "";
                }
                return this._getListFunction(listId, nextPosition, field);
            }
        }
        if (functionName === "ODOO.LIST.HEADER") {
            const field = evaluatedArgs[1];
            if (isColumn) {
                /** Change the field */
                const index = columns.findIndex((col) => col === field) + increment;
                if (index < 0 || index >= columns.length) {
                    return "";
                }
                return this._getListHeaderFunction(listId, columns[index]);
            } else {
                /** If down, set position */
                if (increment > 0) {
                    return this._getListFunction(listId, increment, field);
                }
                return "";
            }
        }
        return formula;
    }

    /**
     * Compute the tooltip to display from a Pivot formula
     *
     * @param {string} formula Pivot formula
     * @param {boolean} isColumn True if the direction is left/right, false
     *                           otherwise
     */
    getTooltipListFormula(formula, isColumn) {
        if (!formula) {
            return [];
        }
        const { functionName, args } = getFirstListFunction(formula);
        const evaluatedArgs = args
            .map(astToFormula)
            .map((arg) => this.getters.evaluateFormula(arg));
        if (isColumn || functionName === "ODOO.LIST.HEADER") {
            const fieldName = functionName === "ODOO.LIST" ? evaluatedArgs[2] : evaluatedArgs[1];
            return this.getters.getListDataSource(evaluatedArgs[0]).getListHeaderValue(fieldName);
        }
        return _t("Record #") + evaluatedArgs[1];
    }

    _getListFunction(listId, position, field) {
        return `=ODOO.LIST(${listId},${position},"${field}")`;
    }

    _getListHeaderFunction(listId, field) {
        return `=ODOO.LIST.HEADER(${listId},"${field}")`;
    }
}

ListAutofillPlugin.getters = ["getNextListValue", "getTooltipListFormula"];
