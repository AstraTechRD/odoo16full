/** @odoo-module **/

import { useService, useAutofocus } from "@web/core/utils/hooks";
import { session } from '@web/session';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { HtmlField } from "@web_editor/js/backend/html_field";
import { useModel } from "@web/views/model";
import { RelationalModel } from "@web/views/relational_model";

const { Component, markup, onWillRender, onWillUnmount, useState, useEffect, useExternalListener, useSubEnv } = owl;

const NOTE_FIELDS = {
    id: {
        name: "id",
        string: "ID",
        readonly: true,
        required: false,
        searchable: true,
        sortable: true,
        store: true,
        type: "integer",
        options: {},
        modifiers: {},
    },
    name: {
        name: "name",
        string: "name",
        readonly: false,
        required: false,
        searchable: true,
        sortable: true,
        store: true,
        type: "char",
        options: {},
        modifiers: {},
    },
    memo: {
        name: "memo",
        string: "Note",
        readonly: false,
        required: false,
        searchable: false,
        sortable: false,
        store: true,
        type: "html",
        options: {},
        modifiers: {},
    },
    color: {
        name: "color",
        string: "Color",
        readonly: true,
        required: false,
        searchable: true,
        sortable: true,
        store: true,
        type: "integer",
        options: {},
        modifiers: {},
    },
    user_id: {
        name: "user_id",
        string: "Owner",
        readonly: true,
        required: false,
        searchable: true,
        sortable: true,
        store: true,
        type: "many2one",
        relation: "res.users",
        options: {},
        modifiers: {},
    },
    tag_ids: {
        name: "tag_ids",
        string: "tags",
        readonly: true,
        required: false,
        searchable: true,
        sortable: true,
        store: true,
        type: "many2many",
        relation: "note.tag",
        options: {},
        modifiers: {},
    },
};

/**
 * This component is actually a dumbed down list view for our notes.
 */

export class PayrollDashboardTodo extends Component {
    setup() {
        this.actionService = useService("action");
        this.user = useService("user");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({
            activeNoteId: -1,
            mode: '',
            isEditingNoteName: false,
        });
        this.autofocusInput = useAutofocus();
        onWillUnmount(() => {
            if (this.state.mode === 'edit') {
                this.saveNote()
            }
        });
        useExternalListener(window, 'beforeunload', (e) => {
            if (this.state.mode === 'edit') {
                this.saveNote();
            }
        });
        onWillRender(() => {
            if (this.state.mode === '' && this.model.root.records.length > 0) {
                this.state.mode = 'readonly';
                this.record = this.model.root.records[0];
            }
        });

        useEffect((el) => {
            if (el) {
                if (["INPUT", "TEXTAREA"].includes(el.tagName)) {
                    el.selectionStart = 0;
                    el.selectionEnd = el.value.length;
                }
            }
        }, () => [this.autofocusInput.el]);

        this.model = useModel(RelationalModel, {
            resModel: "note.note",
            limit: 80,
            fields: NOTE_FIELDS,
            activeFields: NOTE_FIELDS,
            viewMode: "list",
            rootType: "list",
            defaultOrder: {
                name: "id",
                asc: false,
            },
        });
        useSubEnv({ model: this.model });
    }

    get record() {
        return this.model.root.records.find(rec => rec.resId === this.state.activeNoteId);
    }

    set record(record) {
        if (Number.isInteger(record)) {
            this.state.activeNoteId = record;
        } else if (record) {
            this.state.activeNoteId = record.resId;
        } else {
            this.state.activeNoteId = -1;
        }
    }

    /**
     * @returns { Number } id of the session user
     */
    get userId() {
        return session.user_id[0];
    }

    /**
     * Creates a note.
     */
    async createNoteForm() {
        const createdNote = await this.orm.create('note.note', [{
            'name': 'Untitled',
            'tag_ids': [[4, this.props.tagId]],
            'company_id': owl.Component.env.session.user_context.allowed_company_ids[0],
        }]);
        await this.model.load();
        this.record = createdNote;
        this.startNameEdition(this.record);
    }

    /**
     * Switches to the requested note.
     *
     * @param { Record } record
     */
    async onClickNoteTab(record) {
        if (record.resId === this.state.activeNoteId) {
            return;
        }
        if (this.state.mode === 'edit') {
            await this.saveNote();
        }
        this.state.mode = 'readonly';
        this.state.isEditingNoteName = false;
        this.record = record;
    }

    /**
     * On double-click, the note name should become editable
     * @param { Number } noteId 
     */
    startNameEdition(record) {
        if (record.resId === this.state.activeNoteId) {
            this.state.isEditingNoteName = true;
            this.bufferedText = record.data.name;
        }
    }

    /**
     * On input, update buffer
     * @param { Event } ev 
     */
    onInputNoteNameInput(ev) {
        this.bufferedText = ev.target.value;
    }

    /**
     * When the input loses focus, save the changes
     * @param {*} ev
     */
     handleBlur(ev) {
        this._applyNoteRename();
    }

    /**
     * If enter/escape is pressed either save changes or discard them
     * @param { Event } ev 
     */
    onKeyDownNoteNameInput(ev) {
        switch (ev.key) {
            case 'Enter':
                this._applyNoteRename();
                break;
            case 'Escape':
                this.state.isEditingNoteName = false;
                break;
        }
    }

    /**
     * Renames the active note with the text saved in the buffer
     */
    async _applyNoteRename() {
        const value = this.bufferedText.trim();
        if (value !== this.record.data.name) {
            this.record.update({ ["name"]: value });
            await this.record.save();
        }
        this.state.isEditingNoteName = false;
    }

    /**
     * Handler when delete button is clicked
     */
    async onNoteDelete() {
        const message = this.env._t('Are you sure you want to delete this note?');
        this.dialog.add(ConfirmationDialog, {
            body: message,
            confirm: this._deleteNote.bind(this, this.state.activeNoteId),
        });
    }

    /**
     * Deletes the specified note
     * @param {*} noteId 
     */
    async _deleteNote(noteId) {
        await this.model.root.deleteRecords(this.model.root.records.filter(rec => rec.resId === noteId));
        this.record = this.model.root.records[0];
    }

    /**
     * Handles the click on the create note button
     */
    async onClickCreateNote() {
        if (this.state.mode === 'edit') {
            await this.saveNote();
        }
        this.createNoteForm();
    }

    /**
     * Switches the component to edit mode.
     */
    switchToEdit() {
        if (this.state.isEditingNoteName || this.state.mode === 'edit' || this.state.activeNoteId < 0) {
            return;
        }
        this.state.mode = 'edit';
    }

    /**
     * Save the current note, has to be trigger before switching note.
     */
    async saveNote() {
        if (this.record.isDirty) {
            await this.record.save();
        }
    }

    getFieldProps(record) {
        return {
            id: record.id,
            name: "memo",
            fieldName: "memo",
            readonly: this.state.mode === 'readonly',
            record,
            type: "html",
            update: async (value) => {
                await record.update({ ["memo"]: value });
            },
            decorations: {},
            value: record.data.memo == "false" && markup("") || record.data.memo,
            isCollaborative: true,
            wysiwygOptions: {},
        };
    }
}

PayrollDashboardTodo.template = 'hr_payroll.TodoList';
PayrollDashboardTodo.components = {
    HtmlField,
};
