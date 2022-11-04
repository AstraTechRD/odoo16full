odoo.define('pos_settle_due.db', function (require) {
    'use strict';

    const PosDB = require('point_of_sale.DB');
    PosDB.include({
        update_partners: function (partnersWithUpdatedFields) {
            for (const updatedFields of partnersWithUpdatedFields) {
                Object.assign(this.partner_by_id[updatedFields.id], updatedFields);
            }
        },
    });
});
