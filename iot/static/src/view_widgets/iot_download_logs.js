/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { IoTConnectionErrorDialog } from '../iot_connection_error_dialog';

const { Component } = owl;

export class IoTBoxDownloadLogs extends Component {
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.http = useService('http');
    }
    get ip_url() {
        return this.props.record.data.ip_url;
    }
    async downloadLogs() {
        try {
            const response = await this.http.get(this.ip_url + '/hw_proxy/hello', 'text');
            if (response == 'ping') {
                window.location = this.ip_url + '/hw_drivers/download_logs';
            } else {
                this.doWarnFail(this.ip_url);
            }
        } catch (_) {
            this.doWarnFail(this.ip_url);
        }
    }
    doWarnFail(url) {
        this.dialog.add(IoTConnectionErrorDialog, { href: url });
    }
}
IoTBoxDownloadLogs.template = `iot.IoTBoxDownloadLogs`;

registry.category('view_widgets').add('iot_download_logs', IoTBoxDownloadLogs);
