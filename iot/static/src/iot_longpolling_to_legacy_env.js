/** @odoo-module **/

import { registry } from '@web/core/registry';

export function makeIotLongpollingToLegacyEnv(legacyEnv) {
    return {
        dependencies: ['iot_longpolling'],
        start(_, { iot_longpolling }) {
            owl.Component.env.services.iot_longpolling = iot_longpolling;
        },
    };
}

registry.category('wowlToLegacyServiceMappers').add('iot_longpolling_to_legacy_env', makeIotLongpollingToLegacyEnv);

