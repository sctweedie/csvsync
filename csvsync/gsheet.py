from . import config
from .lib import eprint

import pickle
import os.path
import io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import csv

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class Auth:
    def __init__(self, fileconfig):
        self.credfile = fileconfig.expand_config_filename('credentials')
        self.tokenfile = fileconfig.expand_config_filename('token')

        creds = None
        # The file token.pickle stores the user's access and refresh
        # tokens, and is created automatically when the authorization
        # flow completes for the first time.
        if os.path.exists(self.tokenfile):
            with open(self.tokenfile, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credfile, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.tokenfile, 'wb') as token:
                pickle.dump(creds, token)

        self.creds = creds

class Sheet:
    def __init__(self, fileconfig, auth):
        self.fileconfig = fileconfig

        # Find all the sheet tabs from the given spreadsheet

        service = build('sheets', 'v4', credentials = auth.creds).spreadsheets()
        self.service = service
        self.spreadsheet_id = fileconfig['spreadsheet_id']

        sheets_with_properties = \
            self.service \
            .get(spreadsheetId = self.spreadsheet_id, fields = 'sheets.properties') \
            .execute() \
            .get('sheets')

        # If the user has requested a specific sheet/tab by name, find that now.

        find_sheet = fileconfig['sheet']

        self.sheet_id = None

        for sheet in sheets_with_properties:
            if 'title' in sheet['properties'].keys():
                if sheet['properties']['title'] == find_sheet:
                    self.sheet_id = sheet['properties']['sheetId']
                    self.sheet_name = find_sheet
                    break

        assert self.sheet_id != None
        print ('Found sheet "%s" at id %d' % (find_sheet, self.sheet_id))

    def save_to_csv(self, filename, pad_lines = True):
        range = self.sheet_name

        result = self.service \
            .values() \
            .get(spreadsheetId = self.spreadsheet_id, range = range) \
            .execute()

        values = result.get('values', [])

        print ("Loaded %d lines from sheet" % len(values))

        max_len = 0
        for row in values:
            if len(row) > max_len:
                max_len = len(row)

        with open(filename, 'wt') as csvfile:
            csvwriter = csv.writer(csvfile, lineterminator = os.linesep)
            for row in values:
                if pad_lines:
                    while len(row) < max_len:
                        row.append('')
                csvwriter.writerow(row)

    def load_from_csv(self, filename):
        with open(filename, 'rt') as csvfile:
            csvContents = csvfile.read()

        # Count the lines in the CSV (use the proper CSV parser to
        # handle things like newlines embedded in a quoted string).
        #
        # We need a robust line count to make sure we clear the
        # spreadsheet of any additional trailing lines that are no
        # longer needed.

        csvreader = csv.reader(io.StringIO(csvContents))
        lines = 0
        for row in csvreader:
            lines += 1

        eprint ('Uploading %d lines' % lines)

        body = {
            # Use pasteData to insert the new data
            'requests': [{
                'pasteData': {
                    'coordinate': {
                        'sheetId': self.sheet_id,
                        'rowIndex': '0',
                        'columnIndex': '0',
                    },
                    'data': csvContents,
                    'type': 'PASTE_VALUES',
                    'delimiter': ',',
                }
            },
            # and use updateCells with userEnteredValue and no value
            # to clear the remaining rows of the sheet.
            {
                'updateCells': {
                    'range': {
                        'sheetId': self.sheet_id,
                        'startRowIndex': lines,
                    },
                    'fields': 'userEnteredValue'
                }
            }]
        }

        result = self.service \
            .batchUpdate(spreadsheetId = self.spreadsheet_id, body = body) \
            .execute()
