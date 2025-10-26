"""dexterCLI command-line parser."""

import argparse
import configparser
import io
import os
from pathlib import Path
import shutil
import subprocess  # noqa: S404
import sys

from . import VERSION, commands


def main(argv=None):
    """Main entry point for command-line parser."""  # noqa: D401
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
        '--no-pager', '-P', action='store_true',
        help='Do not use a pager to display the output')
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
        '--json', action='store_true',
        help='Output data in JSON format (the default for some commands)')
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Output data verbose format')
    parser.add_argument(
        '--width', '-w', type=int, help='Set the terminal width')
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
            handlers.update(
                dict.fromkeys(command.aliases or (), command.process)
            )

    args = parser.parse_args(argv)
    config = configparser.ConfigParser()
    config.read(Path(args.rcfile).expanduser())
    profile = dict(config.items(args.profile))
    terminal = shutil.get_terminal_size((80, 24))
    if args.api_key:
        profile['api-key'] = args.api_key
    if args.debug:
        profile['debug'] = True
    if args.json:
        profile['json'] = True
    if args.quiet:
        profile['quiet'] = True
    if args.root:
        profile['root'] = args.root
    if args.verbose:
        profile['verbose'] = args.verbose
    if args.width:
        profile['width'] = args.width
    elif not profile.get('width'):
        profile['width'] = (terminal.columns or 80) - 1
    if not profile.get('api-key'):
        parser.error('api-key not specified')
    if not profile.get('root'):
        parser.error('root not specified')
    buffer = None
    if args.output.isatty() and not args.no_pager:
        profile['output'] = buffer = io.StringIO()
    else:
        profile['output'] = args.output
    exit_code = handlers[args.command](profile, args)
    if buffer:
        output = buffer.getvalue()
        pager = os.environ.get('PAGER') or '/bin/more'
        if not os.access(pager, os.X_OK):
            pager = None
        lines = sum(
            1 + len(line) // profile['width']
            for line in output.split('\n')
        )
        if pager and lines > (terminal.lines or 24):
            subprocess.run(  # noqa: S603
                pager,
                check=False,
                input=output,
                stdout=args.output,
                text=True,
            )
        else:
            while output:
                output = output[args.output.write(output):]
    sys.exit(exit_code)
