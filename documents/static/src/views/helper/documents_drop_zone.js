/** @odoo-module **/

const { Component, useEffect, useState } = owl;

export class DocumentsDropZone extends Component {
    setup() {
        this.state = useState({
            dragOver: false,
            topOffset: 0,
        });
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                this.state.topOffset = el.scrollTop;
                const overHandler = this.onDragOver.bind(this);
                const leaveHandler = this.onDragLeave.bind(this);
                const scrollHandler = () => {
                    this.state.topOffset = el.scrollTop;
                };
                el.addEventListener("dragover", overHandler);
                el.addEventListener("dragleave", leaveHandler);
                el.addEventListener("scroll", scrollHandler);
                return () => {
                    el.removeEventListener("dragover", overHandler);
                    el.removeEventListener("dragleave", leaveHandler);
                    el.removeEventListener("scroll", scrollHandler);
                };
            },
            () => [this.props.parentRoot.el],
        );
    }

    get root() {
        return this.props.parentRoot;
    }

    onDragOver(ev) {
        if (!this.env.searchModel.getSelectedFolderId() || !ev.dataTransfer.types.includes("Files")) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        if (this.root && this.root.el && !this.root.el.classList.contains("o_documents_drop_over")) {
            this.root.el.classList.add("o_documents_drop_over");
        }
        this.state.dragOver = true;
    }

    onDragLeave(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (this.root && this.root.el) {
            this.root.el.classList.remove("o_documents_drop_over");
        }
        this.state.dragOver = false;
    }

    async onDrop(ev) {
        if (!this.env.searchModel.getSelectedFolderId() || !ev.dataTransfer.types.includes("Files")) {
            return;
        }
        if (this.root && this.root.el) {
            this.root.el.classList.remove("o_documents_drop_over");
        }
        this.state.dragOver = false;
        await this.env.documentsView.bus.trigger("documents-upload-files", {
            files: ev.dataTransfer.files,
            folderId: this.env.searchModel.getSelectedFolderId(),
            recordId: false,
            tagIds: this.env.searchModel.getSelectedTagIds(),
        });
    }
}
DocumentsDropZone.template = "documents.DocumentsDropZone";
