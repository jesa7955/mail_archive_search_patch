""" Configuration file and options parsing """

import argparse
import configparser
import os
import sys

CONFIG_GLOBAL = os.path.expanduser("~/.list_archive")
CONFIG_LOCAL = os.path.expanduser("./config")

class GeneralConfig(object):
    """ General option class """
    def __init__(self, arguments=None):
        self.parser = None
        self.name = None
        self.email = None
        self.month = None
        self.year = None
        self.lkml = []
        self.spinics = []
        self.pipermail = {}
        self.hyperkitty = {}
        self._get_options(arguments)

    def _get_options(self, arguments=None):
        raise NotImplementedError

class Config(GeneralConfig):
    """ Parse configuration file and command line arguments """
    def _get_options(self, arguments=None):
        self.parser = configparser.ConfigParser()

        try:
            self.parser.read_file(open(CONFIG_GLOBAL))
            CONFIG = CONFIG_GLOBAL
        except FileNotFoundError:
            print('No configuration file {0} was found, searching in the current path'.format(CONFIG_GLOBAL), file=sys.stderr)
            try:
                self.parser.read_file(open(CONFIG_LOCAL))
                CONFIG = CONFIG_LOCAL
            except FileNotFoundError:
                print('Configuration file {0} not found, exiting...'.format(CONFIG_LOCAL), file=sys.stderr)
                sys.exit(1)
        print('Using configuration file {0}'.format(CONFIG), file=sys.stderr)
        try:
            self.name = self.parser['general']['name']
            self.email = [mail.strip() for mail in
                          self.parser['general']['email'].split()]
        except KeyError as key_not_found:
            print('{0} not configured in {1}'.format(key_not_found, CONFIG), file=std.stderr)
            sys.exit(1)

        for section in self.parser.sections():
            if section == 'general':
                continue
            elif section == 'lkml' or section == 'LKML':
                self.lkml = True
                continue
            list_type = self.parser[section]['type']
            list_names = self.parser[section]['listnames'].split()
            if list_type == 'pipermail':
                list_url = self.parser[section]['url']
                self.pipermail.update({list_url: list_names})
            elif list_type == 'hyperkitty':
                list_url = self.parser[section]['url']
                self.hyperkitty.update({list_url: list_names})
            elif list_type == 'spinics':
                self.spinics = list_names
        if arguments is None:
            return
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--month')
        self.parser.add_argument('--year')
        opt, args = self.parser.parse_known_args(arguments)
        if opt.month and opt.year:
            self.month = int(opt.month)
            self.year = int(opt.year)
        else:
            print("No year and month is specified")
            sys.exit(1)

class Options(GeneralConfig):
    """ Parse command line options(deprecated) """
    def _get_options(self, arguments=None):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--name')
        self.parser.add_argument('--email', nargs='*')
        self.parser.add_argument('--month')
        self.parser.add_argument('--year')
        self.parser.add_argument('--rh_internal')
        self.parser.add_argument('--pipermail')
        self.parser.add_argument('--hyperkitty')
        self.parser.add_argument('--spinics')

        if not arguments:
            # No CMD line arguments, used with config file
            return
        opt, args = self.parser.parse_known_args(arguments)
        self.rh_internal = [mailing_list for mailing_list in args if
                            mailing_list != 'lkml']
        self.lkml = 'lkml' in args
        self.rh_internal = self._get_list_name(opt.rh_internal)
        self.pipermail = self._get_list_name(opt.pipermail)
        self.hyperkitty = self._get_list_name(opt.hyperkitty)
        self.spinics = self._get_list_name(opt.spinics)
        self.month = int(opt.month)
        self.year = int(opt.year)
        self.name = opt.name
        self.email = opt.email
        if not all([self.email, self.name, self.month, self.year]):
            print('Make sure you have specified email, name, month and year')
            self.email = None

    def _get_list_name(self, opt):
        if opt:
            return opt.split()
        else:
            return []
