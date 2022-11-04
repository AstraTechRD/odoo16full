
from odoo.addons.documents.controllers.main import ShareRoute

class SpreadsheetShareRoute(ShareRoute):

    def _get_downloadable_documents(self, documents):
        """
            override of documents to prevent the download
            of spreadsheets binary as they are not usable
        """
        return documents.filtered(lambda doc: doc.mimetype != "application/o-spreadsheet")
