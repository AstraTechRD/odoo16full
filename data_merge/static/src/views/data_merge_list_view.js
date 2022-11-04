/** @odoo-module **/

import { DataCleaningCommonListController } from "@data_recycle/views/data_cleaning_common_list";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

export class DataMergeListModel extends listView.Model {}
export class DataMergeListRecord extends DataMergeListModel.Record {
    /**
    * @override
    */
    async _save() {
        await super._save(...arguments);
        await this.model.load();
        this.model.notify();
    }
}
DataMergeListModel.Record = DataMergeListRecord;

export class DataMergeListController extends DataCleaningCommonListController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        const onClickViewButton = this.env.onClickViewButton;

        owl.useSubEnv({
            onClickViewButton: (params) => {
                const paramsName = params.clickParams.name;
                const ResParams = params.getResParams();
                const groupId = ResParams.resId;
                const groupRecords = this.getGroupRecords(groupId);
                const recordIds = this.getRecordIDS(groupRecords);
                const action = (paramsName === 'merge_records' ? 'merge_records' : 'discard_records');

                if (action === 'merge_records') {
                    this.dialog.add(ConfirmationDialog, {
                        body: this.env._t("Are you sure that you want to merge these records?"),
                        confirm: async () => {
                            await this.doActionMergeDiscard(action, groupId, recordIds);
                        },
                        cancel: () => {},
                    });
                } else if (action === 'discard_records') {
                    this.doActionMergeDiscard(action, groupId, recordIds);
                } else {
                    onClickViewButton(params);
                }
            },
        });
    }

    /**
     * Get the list of selected records for the specified group
     * @returns list of record IDs
     * @param {int} groupId
     */
    getGroupRecords(groupId) {
        let records = this.model.root.selection;
        if (!this.model.root.selection.length) {
            records = this.model.root.records;
        }
        return records.filter(record => record.data.group_id[0] === groupId);
    }

    /**
     * Get the original record IDs
     * @param {int[]} records
     */
    getRecordIDS(records) {
        return records.map(record => parseInt(record.resId));
    }

    /**
     * Call the specified action
     * @param {string} action Action to perform (merge/discard)
     * @param {int} groupId ID of the data_merge.group
     * @param {int[]} recordIds Selected records to merge/discard
     */
    async _callAction(action, groupId, recordIds) {
        return this.orm.call('data_merge.group', action, [groupId, recordIds]);
    }

    /**
     * Merge all the selected records
     */
    onValidateClick(ev) {
        const records = this.model.root.selection;
        let group_ids = {};

        records.forEach(function(record) {
            const group_id = parseInt(record.data.group_id[0]);
            let ids = group_ids[group_id] || [];
            ids.push(parseInt(record.resId));
            group_ids[group_id] = ids;
        });


        this.dialog.add(ConfirmationDialog, {
            body: this.env._t("Are you sure that you want to merge the selected records in their respective group?"),
            confirm: async () => {
                this.orm.call('data_merge.group', 'merge_multiple_records', [group_ids]);
                this.showMergeNotification();
                records.forEach(record => this.model.root.removeRecord(record));
                this.model.root.groups
                    .filter(group => !group.count)
                    .forEach(group => this.model.root.removeGroup(group));
                await this.model.load();
                this.model.notify();
            },
            cancel: () => {},
        });
    }

    async doActionMergeDiscard(action, groupId, recordIds) {
        let res = await this._callAction(action, groupId, recordIds)
        if (res && 'type' in res && res.type.startsWith('ir.actions')) {
            if(!('views' in res)) {
                res = Object.assign(res, {views: [[false, 'form']]});
            }
            this.actionService.doAction(res)
        } else if (res && res.back_to_model) {
            window.history.back();
        } else {
            if (action === 'merge_records') {
                const records_merged = res && 'records_merged' in res ? res.records_merged : false;
                this.showMergeNotification(records_merged);
            }
            this.model.root.records
                .filter(record => record.resId in recordIds)
                .forEach(record => this.model.root.removeRecord(record));
            this.model.root.removeGroup(this.model.root.groups
                .filter(group => group.resId === groupId));
            await this.model.load();
            this.model.notify();
        }
    }

    /**
     * Show a notification with the number of records merged
     * @param {int} records_merged
     */
    showMergeNotification(recordsMerged) {
        let message;
        if (recordsMerged) {
            message = sprintf(this.env._t("%s records have been merged"), recordsMerged);
        } else {
            message = this.env._t("The selected records have been merged");
        }
        this.notificationService.add(message, {});
    }
};

registry.category('views').add('data_merge_list', {
    ...listView,
    Controller: DataMergeListController,
    Model: DataMergeListModel,
    buttonTemplate: 'DataMergeListView.buttons',
});

