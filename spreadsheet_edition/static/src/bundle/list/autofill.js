/** @odoo-module */

import { getNumberOfListFormulas } from "@spreadsheet/list/list_helpers";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { autofillModifiersRegistry, autofillRulesRegistry } = spreadsheet.registries;

const UP = 0;
const DOWN = 1;
const LEFT = 2;
const RIGHT = 3;

//--------------------------------------------------------------------------
// Autofill Rules
//--------------------------------------------------------------------------

autofillRulesRegistry
    .add("autofill_list", {
        condition: (cell) =>
            cell && cell.isFormula() && getNumberOfListFormulas(cell.content) === 1,
        generateRule: (cell, cells) => {
            const increment = cells.filter(
                (cell) =>
                    cell &&
                    cell.isFormula()&&
                    getNumberOfListFormulas(cell.content) === 1
            ).length;
            return { type: "LIST_UPDATER", increment, current: 0 };
        },
        sequence: 3,
    });

//--------------------------------------------------------------------------
// Autofill Modifier
//--------------------------------------------------------------------------

autofillModifiersRegistry
    .add("LIST_UPDATER", {
        apply: (rule, data, getters, direction) => {
            rule.current += rule.increment;
            let isColumn;
            let steps;
            switch (direction) {
                case UP:
                    isColumn = false;
                    steps = -rule.current;
                    break;
                case DOWN:
                    isColumn = false;
                    steps = rule.current;
                    break;
                case LEFT:
                    isColumn = true;
                    steps = -rule.current;
                    break;
                case RIGHT:
                    isColumn = true;
                    steps = rule.current;
            }
            const content = getters.getNextListValue(
                getters.getFormulaCellContent(data.sheetId, data.cell),
                isColumn,
                steps
            );
            let tooltip = {
                props: {
                    content,
                },
            };
            if (content && content !== data.content) {
                tooltip = {
                    props: {
                        content: getters.getTooltipListFormula(content, isColumn),
                    },
                };
            }
            return {
                cellData: {
                    style: undefined,
                    format: undefined,
                    border: undefined,
                    content,
                },
                tooltip,
            };
        },
    });
