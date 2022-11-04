/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { SearchModel } from "@web/search/search_model";

export class MrpMpsSearchModel extends SearchModel {
    /**
     * When search with field bom_id, also show components of that bom
     * 
     * @override
     */
    _getFieldDomain(field, autocompleteValues) {
        let domain = super._getFieldDomain(...arguments);
        if (field.fieldName === "bom_id") {
            const additionalDomain = [
                "|",
                    ["product_id.bom_line_ids.bom_id", "ilike", autocompleteValues[0].value],
                    "|",
                        ["product_id.variant_bom_ids", "ilike", autocompleteValues[0].value],
                        "&",
                            ["product_tmpl_id.bom_ids.product_id", "=", false],
                            ["product_tmpl_id.bom_ids", "ilike", autocompleteValues[0].value],
            ];
            domain = Domain.or([additionalDomain, domain.toList()]);
        }
        return domain;
    }
};
