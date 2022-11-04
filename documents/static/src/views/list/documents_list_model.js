/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { DocumentsModelMixin, DocumentsDataPointMixin, DocumentsRecordMixin } from "../documents_model_mixin";

const ListModel = listView.Model;
export class DocumentsListModel extends DocumentsModelMixin(ListModel) {}

DocumentsListModel.Record = class DocumentsListRecord extends DocumentsRecordMixin(ListModel.Record) {};
DocumentsListModel.Group = class DocumentsListGroup extends DocumentsDataPointMixin(ListModel.Group) {};
DocumentsListModel.DynamicRecordList = class DocumentsListDynamicRecordList extends DocumentsDataPointMixin(ListModel.DynamicRecordList) {};
DocumentsListModel.DynamicGroupList = class DocumentsListDynamicGroupList extends DocumentsDataPointMixin(ListModel.DynamicGroupList) {};
DocumentsListModel.StaticList = class DocumentsListStaticList extends DocumentsDataPointMixin(ListModel.StaticList) {};
