odoo.define('account_consolidation.GridRenderer', function (require) {
    "use strict";

    const GridRenderer = require('web_grid.GridRenderer');

    class AccountConsolidationGridRenderer extends GridRenderer {

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * @override
         */
        get gridTotal() {
            const total = super.gridTotal;
            if (this.props.totals.super) {
                total.classMap['text-danger'] = false;
                total.classMap.o_not_zero = this.props.totals.super !== 0;
            }
            return total;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _getCellClassMap(cell) {
            const classMap = super._getCellClassMap(...arguments);
            classMap.o_grid_cell_empty = classMap.o_grid_cell_empty || cell.value === 0;
            return classMap;
        }
    }

    return AccountConsolidationGridRenderer;
});
