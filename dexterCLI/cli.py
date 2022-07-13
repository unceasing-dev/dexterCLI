"""dexterCLI command-line parser"""

import argparse
import configparser
import os.path
import sys

from . import VERSION, commands


def main(argv=None):
    """Main entry point for command-line parser"""
    parser = argparse.ArgumentParser(
        description='Dexter API command-line interface',
        prog='dexter')
    parser.add_argument(
        '--api-key', help='The API key to use')
    parser.add_argument(
        '--debug', '-d', action='store_true', help='Display debug output')
    parser.add_argument(
        '--output', '-o', metavar='FILENAME', type=argparse.FileType('w'),
        default=sys.stdout, help='The file to write the output to')
    parser.add_argument(
        '--profile', '-p', default='default',
        help='The configuration profile to use (default: default)')
    parser.add_argument(
        '--quiet', '-q', action='store_true', help='No output')
    parser.add_argument(
        '--rcfile', default='~/.dexter.conf',
        help='The configuration file to load (default: ~/.dexter.conf)')
    parser.add_argument(
        '--root', help='The root URL of the API interface')
    parser.add_argument(
        '--version', '-V', action='version',
        help='Display the version number and exit',
        version='dexter ' + VERSION)
    subparsers = parser.add_subparsers(dest='command', required=True)
    handlers = {}
    for command in dir(commands):
        if command.startswith('_'):
            continue
        command = getattr(commands, command)
        try:
            valid = (issubclass(command, commands.Base) and
                     command is not commands.Base)
        except TypeError:
            valid = False
        if valid:
            name = command.name or command.__name__.lower()
            command.add_arguments(subparsers.add_parser(
                name,
                aliases=command.aliases or (),
                description=command.description,
            ))
            handlers[name] = command.process

    args = parser.parse_args(argv)
    config = configparser.ConfigParser()
    config.read(os.path.expanduser(args.rcfile))
    profile = dict(config.items(args.profile))
    if args.api_key:
        profile['api-key'] = args.api_key
    if args.debug:
        profile['debug'] = True
    if args.quiet:
        profile['quiet'] = True
    if args.root:
        profile['root'] = args.root
    profile['output'] = args.output
    if not profile.get('api-key'):
        parser.error('api-key not specified')
    if not profile.get('root'):
        parser.error('root not specified')
    sys.exit(handlers[args.command](profile, args))
