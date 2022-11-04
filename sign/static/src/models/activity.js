/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/activity';

registerPatch({
   name: 'Activity',
   recordMethods: {
        async requestSignature() {
            return new Promise(resolve => {
                this.env.services.action.doAction(
                    {
                        name: this.env._t("Signature Request"),
                        type: 'ir.actions.act_window',
                        view_mode: 'form',
                        views: [[false, 'form']],
                        target: 'new',
                        res_model: 'sign.send.request',
                    },
                    {
                        additionalContext: {
                            'sign_directly_without_mail': false,
                            'default_activity_id': this.id,
                        },
                        onClose: resolve,
                    },
                );
            });
        },
    },
});
