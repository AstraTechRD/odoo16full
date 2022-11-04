/** @odoo-module */

import { KanbanModel } from '@web/views/kanban/kanban_model';
import { FsmProductRecord } from './fsm_product_record';

export class FsmProductKanbanModel extends KanbanModel { }

FsmProductKanbanModel.Record = FsmProductRecord;
