"""dexterCLI commands"""

import argparse
import datetime
import json
import re

import requests

from .api import api, parse_date


class Base:
    """Base class for dexterCLI commands"""
    aliases = None
    description = None
    name = None

    @classmethod
    def add_arguments(cls, parser):
        """Add arguments, if any, to the argument parser."""

    @classmethod
    def process(cls, profile, args):
        """Process a command."""
        raise NotImplementedError

    @classmethod
    def display_response(cls, profile, response, table=None):
        """Display the output from an API call"""
        if profile.get('debug') or not profile.get('quiet'):
            if response.status_code != 200 or profile.get('debug'):
                profile['output'].write(
                    f'{response.status_code} {response.reason}\n')
            if response.headers.get('location'):
                profile['output'].write(
                    f'Location: {response.headers["location"]}')
            if (response.content and (profile.get('verbose') or not table)
                    and not profile.get('json')):
                data = response.json()
                if len(data) == 1 and 'reports' in data:
                    data = data['reports']
                if not data:
                    profile['output'].write('No results\n')
                else:
                    cls.display_verbose(profile, data)
                    profile['output'].write('\n')
            elif table and not profile.get('json'):
                cls.display_table(profile, table)
            elif response.content:
                json.dump(response.json(), profile['output'], indent=2)
                profile['output'].write('\n')
        if 200 <= response.status_code < 300:
            return 0  # EX_OK
        return 74  # EX_IOERR

    @classmethod
    def display_verbose(cls, profile, data, indent=''):
        if data is None:
            profile['output'].write('null')
        elif isinstance(data, str):
            profile['output'].write(
                data if data.isprintable() else repr(data))
        elif isinstance(data, bool):
            profile['output'].write('true' if data else 'false')
        elif isinstance(data, (int, float)):
            profile['output'].write(f'{data:,}')
        elif isinstance(data, list):
            if data:
                if indent:
                    profile['output'].write('\n')
                for row, value in enumerate(data):
                    profile['output'].write(indent)
                    cls.display_verbose(profile, value, indent + '    ')
                    if row < len(data) - 1:
                        profile['output'].write('\n')
        elif isinstance(data, dict):
            if data:
                if indent:
                    profile['output'].write('\n')
                for row, (key, value) in enumerate(data.items()):
                    profile['output'].write(indent + f'{key}: ')
                    cls.display_verbose(profile, value, indent + '    ')
                    if row < len(data) - 1:
                        profile['output'].write('\n')
        else:
            raise ValueError(f'Cannot handle value of type {type(data)}')

    @classmethod
    def display_table(cls, profile, table):
        header = list(table.pop(0))
        if not table:
            profile['output'].write('No results\n')
            return
        align = ['<'] * len(header)
        min_widths = [None] * len(header)
        padding = '-|-'
        for col, field in enumerate(header):
            match = re.match(r'(\d*)([<>^])(.*)$', field)
            if match:
                if match.group(1):
                    min_widths[col] = int(match.group(1))
                align[col] = match.group(2)
                header[col] = match.group(3)
        widths = [len(head) for head in header]
        for rownum, row in enumerate(table):
            if not isinstance(row, list):
                table[rownum] = row = list(row)
            for col, column in enumerate(row):
                row[col] = column = str(column)
                if len(column) > widths[col]:
                    widths[col] = len(column)
        while True:
            total_width = sum(widths) + len(padding) * len(widths) - 1
            if total_width <= profile['width']:
                break
            if len(padding) > 1:
                padding = '|'
                continue
            for col in range(len(widths) - 1, -1, -1):
                if (min_widths[col] and widths[col] > min_widths[col]):
                    widths[col] = max(
                        widths[col] - (total_width - profile['width']),
                        min_widths[col]
                    )
                    break
            else:
                break
        for row, data in enumerate([header] + table):
            profile['output'].write(
                (' ' * len(padding)).join(
                    f'{column[:widths[col]]:{align[col]}{widths[col]}}'
                    for col, column in enumerate(data)
                ) + '\n'
            )
            if row == 0:
                profile['output'].write(
                    padding.join('-' * width for width in widths) + '\n'
                )


class List(Base):
    """List reports"""
    description = 'List reports'

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '--user', help='Display reports requested by this user')
        parser.add_argument(
            'status',
            choices=('incomplete', 'queued', 'running', 'callback',
                     'complete', 'all'),
            nargs='*', default='incomplete',
            help='Display reports that are in this status')

    @staticmethod
    def sort_key(report):
        return (
            {
                'queued': 2,
                'running': 0,
                'callback': 1,
                'complete': 3,
            }.get(report['status'], 1),
            -report['priority'],
            report['queued'],
        )


    @classmethod
    def process(cls, profile, args):
        statuses = set([args.status] if isinstance(args.status, str)
                       else args.status)
        if 'all' in statuses:
            statuses.clear()
        elif 'incomplete' in statuses:
            statuses |= {'queued', 'running', 'callback'}
            statuses.remove('incomplete')
        params = [('status', status) for status in statuses]
        if args.user is not None:
            params.append(('user', args.user))
        response = api(profile, 'reports', params=params)
        reports = list(response.json().get('reports', {}).values())
        reports.sort(key=cls.sort_key)
        output = [['20<URL', '>Pri', '4^Status', '>Pages', '>Age']]
        for report in reports:
            pages = f'{report["pages"]:,}'
            if report['status'] == 'queued':
                pages = f'{report["requestedPages"]:,}'
            elif report['status'] == 'running':
                pages = f'{report["pages"]:,}/{report["requestedPages"]:,}'
            output.append((
                report['url'],
                report['priority'],
                report['status'],
                pages,
                cls.age(parse_date(report['queued'])),
            ))
        return cls.display_response(profile, response, output)


    @staticmethod
    def age(time):
        """Return the age of the datetime"""
        age = int((datetime.datetime.utcnow() - time).total_seconds())
        if age < 60:
            return '{}s'.format(age)
        if age < 60 * 60:
            return '{}m'.format(age // 60)
        if age < 48 * 60 * 60:
            return '{}h'.format(age // 3600)
        return '{}d'.format(age // 86400)


class Queue(Base):
    """Queue a report"""
    description = 'Queue a report'

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '--callback', metavar='URL', help='The callback URL')
        parser.add_argument(
            '--callback-id', metavar='ID', help='The callback ID')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--config', help='The configuration')
        group.add_argument(
            '--config-file', type=argparse.FileType(), metavar='FILENAME',
            help='Read the configuration from this file')
        parser.add_argument(
            '--lifetime', metavar='DAYS', type=int,
            help='The report lifetime')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--metadata', metavar='JSON', help='The metadata')
        group.add_argument(
            '--metadata-file', type=argparse.FileType(), metavar='FILENAME',
            help='Read the metadata from this file')
        parser.add_argument('url', metavar='URL', help='The start URL')
        parser.add_argument(
            'pages', default=1, nargs='?', type=int,
            help='The number of pages to scan (default: 1)')

    @classmethod
    def process(cls, profile, args):
        data = {'url': args.url, 'requestedPages': args.pages}
        if args.callback:
            data['callback'] = args.callback
        if args.callback_id:
            data['callbackId'] = args.callbackId
        if args.config:
            data['config'] = args.config
        if args.config_file:
            data['config'] = args.config_file.read()
        if args.lifetime:
            data['lifetime'] = args.lifetime
        if args.metadata:
            data['metadata'] = json.loads(args.metadata)
        if args.metadata_file:
            data['metadata'] = json.load(args.metadata_file)
        return cls.display_response(
            profile, api(profile, 'reports', data=data))


class Update(Base):
    """Update the metadata of a report"""
    description = 'Update the metadata of a report'

    @classmethod
    def add_arguments(cls, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--metadata', metavar='JSON', help='The metadata')
        group.add_argument(
            '--metadata-file', type=argparse.FileType(), metavar='FILENAME',
            help='Read the metadata from this file')
        parser.add_argument(
            'report', metavar='ID', help='The report ID or its status URL')

    @classmethod
    def process(cls, profile, args):
        if args.metadata:
            data = {'metadata': json.loads(args.metadata)}
        else:
            data = {'metadata': json.load(args.metadata_file)}
        return cls.display_response(
            profile,
            api(profile, args.report, base='reports/', data=data,
                method='PUT')
        )


class Status(Base):
    """Display the status of a report"""
    aliases = ('info',)
    description = 'Display the status of a report'

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            'report', metavar='ID', help='The report ID or its status URL')

    @classmethod
    def process(cls, profile, args):
        return cls.display_response(
            profile, api(profile, args.report, base='reports/'))


class Delete(Base):
    """Delete a report"""
    description = 'Delete a report'
    aliases = ('cancel',)

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            'report', metavar='ID', help='The report ID or its status URL')

    @classmethod
    def process(cls, profile, args):
        return cls.display_response(
            profile,
            api(profile, args.report, base='reports/', method='DELETE')
        )


class Fetch(Base):
    """Fetch a full report"""
    description = 'Fetch a full report'

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            'report', metavar='ID', help='The report ID or its status URL')

    @classmethod
    def process(cls, profile, args):
        response = api(profile, args.report, base='reports/')
        if response.status_code != 200:
            return cls.display_response(profile, response)
        if profile.get('debug'):
            cls.display_response(profile, response)
        report = response.json().get('detail')
        if not report:
            if not profile.get('quiet'):
                profile['output'].write('Report is not available yet\n')
            return 74  # EX_IOERR
        return cls.display_response(profile, requests.get(report, timeout=30))
