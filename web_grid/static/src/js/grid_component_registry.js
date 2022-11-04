odoo.define('web_grid.component_registry', function (require) {
    "use strict";

    const Registry = require('web.Registry');

    return new Registry();
});

odoo.define('web_grid._component_registry', function (require) {
    "use strict";

    const components = require('web_grid.components');
    const registry = require('web_grid.component_registry');

    registry
        .add('float_factor', components.FloatFactorComponent)
        .add('float_time', components.FloatTimeComponent)
        .add('float_toggle', components.FloatToggleComponent);
});
