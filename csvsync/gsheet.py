from . import config
from .lib import eprint

import pickle
import os.path
import io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import csv

import csvdiff3

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

        service = build('sheets', 'v4', credentials = auth.creds, cache_discovery = False).spreadsheets()
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

        print (f'Loaded {len(values)} lines from sheet')

        max_len = max([len(row) for row in values])

        quote = self.fileconfig["quote"]
        lineterminator = self.fileconfig["lineterminator"]
        options = csvdiff3.tools.Options(quote = quote, lineterminator = lineterminator)

        with open(filename, 'wt') as csvfile:
            csvwriter = csv.writer(csvfile, **options.csv_kwargs())
            for row in values:
                if pad_lines:
                    row += [''] * (max_len - len(row))
                csvwriter.writerow(row)

    def load_from_csv(self, filename):
        values = []

        # Read in the CSV file

        with open(filename, 'rt') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                values.append(row)

        # Now construct a list of google API-compatible rows from that data

        rowdata = []
        for row in values:
            cells = []
            for cell in row:
                if isinstance(cell, int) or isinstance(cell, float):
                    celltype = "numberValue"
                    cellval = float(cell)
                else:
                    celltype = "stringValue"
                    cellval = str(cell)
                cells.append({
                    'userEnteredValue':
                    {
                        celltype: cellval
                    }
                })
            rowdata.append({
                'values': cells
                })

        requests = [
            # Update the main content of the spreadsheet with the new
            # values constructed from the CSV.  A startRowIndex of 0
            # with no endRowIndex will cause a complete replace of the
            # sheet, including culling any trailing lines beyond the
            # data uploaded.
            {
                'updateCells': {
                    'range': {
                        'sheetId': self.sheet_id,
                        'startRowIndex': 0,
                    },
                    'fields': 'userEnteredValue',
                    'rows': rowdata
                }
            }]

        body = {
            'requests': requests
        }

        eprint (f'Uploading {len(values)} lines...')

        result = self.service \
            .batchUpdate(spreadsheetId = self.spreadsheet_id,
                         body = body
            ).execute()
