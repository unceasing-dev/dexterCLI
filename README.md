# dexter command-line interface

## Installation

    pip install dexterCLI

## Configuration

You can store settings in an INI-style configuration file, which by default
will be looked for in `~/.dexter.conf`. It can contained named sections,
each of which is a different configuration profile. The default profile is
called `default`. The two main keys needed are `root` and `api-key` which
respectively specify the root URL of the API interface, and the API key to
use.

Example:

    [default]
    root = https://api.dexter.express/
    api-key = 1234567812345678

## Usage

    usage: dexter [-h] [--api-key API_KEY] [--debug] [--output FILENAME]
                  [--profile PROFILE] [--quiet] [--rcfile RCFILE] [--root ROOT]
                  [--version]
                  {delete,cancel,fetch,list,queue,status,info,update} ...

    Dexter API command-line interface

    positional arguments:
      {delete,cancel,fetch,list,queue,status,info,update}

    optional arguments:
      -h, --help            show this help message and exit
      --api-key API_KEY     The API key to use
      --debug, -d           Display debug output
      --output FILENAME, -o FILENAME
                            The file to write the output to
      --profile PROFILE, -p PROFILE
                            The configuration profile to use (default: default)
      --quiet, -q           No output
      --rcfile RCFILE       The configuration file to load (default:
                            ~/.dexter.conf)
      --root ROOT           The root URL of the API interface
      --version, -V         Display the version number and exit

