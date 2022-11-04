/** @odoo-module **/

import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export const iotBoxListView = {
    ...listView,
    buttonTemplate: 'iot.iot_box.ListView.Buttons',
};

registry.category('views').add('box_list_view', iotBoxListView);
