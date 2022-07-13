"""dexterCLI commands"""

import argparse
import json

import requests

from .api import api


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
    def display_response(cls, profile, response):
        """Display the output from an API call"""
        if profile.get('debug') or not profile.get('quiet'):
            if response.status_code != 200 or profile.get('debug'):
                profile['output'].write(
                    f'{response.status_code} {response.reason}\n')
            if response.headers.get('location'):
                profile['output'].write(
                    f'Location: {response.headers["location"]}')
            if response.content:
                json.dump(response.json(), profile['output'], indent=2)
                profile['output'].write('\n')
        if 200 <= response.status_code < 300:
            return 0  # EX_OK
        return 74  # EX_IOERR


class List(Base):
    """List reports"""
    description = 'List reports'

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            '--user', help='Display reports requested by this user')
        parser.add_argument(
            'status',
            choices=('queued', 'running', 'callback', 'complete', 'all'),
            nargs='*', default='all',
            help='Display reports that are in this status')

    @classmethod
    def process(cls, profile, args):
        params = [
            ('status', status)
            for status in (args.status if args.status != 'all' else ())
        ]
        if args.user is not None:
            params.append(('user', args.user))
        return cls.display_response(
            profile, api(profile, 'reports', params=params))


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
