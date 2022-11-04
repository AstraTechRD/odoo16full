odoo.define('l10n_de_pos_cert.utils', function(require) {
    'use strict';

    /*
     *  Convert a timestamp measured in seconds since the Unix epoch. String format returned YYYY-MM-DDThh:mm:ss
     */

    function convertFromEpoch(seconds) {
        return new Date(seconds * 1000).toISOString().substring(0,19).replace('T',' ');
    };

    return { convertFromEpoch };
});
