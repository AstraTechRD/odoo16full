odoo.define('website_helpdesk.form', function (require) {
'use strict';

var core = require('web.core');
var FormEditorRegistry = require('website.form_editor_registry');

var _t = core._t;

FormEditorRegistry.add('create_ticket', {
    formFields: [{
        type: 'char',
        required: true,
        name: 'partner_name',
        fillWith: 'name',
        string: 'Your Name',
    }, {
        type: 'email',
        required: true,
        name: 'partner_email',
        fillWith: 'email',
        string: 'Your Email',
    }, {
        type: 'char',
        modelRequired: true,
        name: 'name',
        string: 'Subject',
    }, {
        type: 'char',
        name: 'description',
        string: 'Description',
    }, {
        type: 'binary',
        custom: true,
        name: 'Attachment',
    }],
    fields: [{
        name: 'team_id',
        type: 'many2one',
        relation: 'helpdesk.team',
        string: _t('Helpdesk Team'),
    }],
    successPage: '/your-ticket-has-been-submitted',
});

});
