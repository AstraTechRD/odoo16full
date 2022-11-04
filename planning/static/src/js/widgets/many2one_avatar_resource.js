/** @odoo-module **/

import fieldRegistry from 'web.field_registry';
import { Many2OneAvatar } from 'web.relational_fields';

export const Many2OneAvatarResource = Many2OneAvatar.extend({
    _template: 'planning.Many2OneResourceAvatar',

    fieldDependencies: Object.assign({}, Many2OneAvatar.prototype.fieldDependencies, {
        resource_type: { type: 'selection' },
   }),

});

fieldRegistry.add('many2one_avatar_resource', Many2OneAvatarResource);
