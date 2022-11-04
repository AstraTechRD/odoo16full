/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
const { otRegistry } = spreadsheet.registries;

otRegistry.addTransformation(
  "REMOVE_GLOBAL_FILTER",
  ["EDIT_GLOBAL_FILTER"],
  (toTransform, executed) =>
    toTransform.id === executed.id ? undefined : toTransform
);
