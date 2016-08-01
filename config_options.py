""" Configuration file and options parsing """

import argparse
import configparser
import os

CONFIG = os.path.expanduser("~/.list_archive")


class GeneralConfig(object):
    """ General option class """
    parser = None
    name = None
    email = None
    lkml = None
    rh_internal = None
    month = None
    year = None

    def __init__(self, arguments=None):
        self._get_options(arguments)

    def _get_options(self, arguments=None):
        raise NotImplementedError


class Config(GeneralConfig):
    """ Parse configuration file if command options are missing """
    parser = configparser.ConfigParser()

    def _get_options(self, arguments=None):
        try:
            self.parser.read_file(open(CONFIG))
            self.month = int(self.parser['general']['month'])
            self.year = int(self.parser['general']['year'])
            self.name = self.parser['general']['name']
            self.email = [mail for mail in
                          self.parser['general']['email'].split(',')]
        except FileNotFoundError:
            print('Configuration file {0} not found'.format(CONFIG))
        except KeyError as key_not_found:
            print('{0} not configured in {1}'.format(key_not_found, CONFIG))
        self.lkml = 'LKML' in self.parser.sections()
        try:
            self.rh_internal = [mailing_list for mailing_list in
                                self.parser['RH']['lists'].split(',')]
        except KeyError:
            self.rh_internal = []


class Options(GeneralConfig):
    """ Parse command line options """
    parser = argparse.ArgumentParser()
    parser.add_argument('--name')
    parser.add_argument('--email', nargs='*')
    parser.add_argument('--month')
    parser.add_argument('--year')

    def _get_options(self, arguments=None):
        if not len(arguments):
            # No CMD line arguments, used with config file
            return
        opt, args = self.parser.parse_known_args(arguments)
        self.rh_internal = [mailing_list for mailing_list in args if
                            mailing_list != 'lkml']
        self.lkml = 'lkml' in args
        self.month = int(opt.month)
        self.year = int(opt.year)
        self.name = opt.name
        self.email = opt.email
        if not all([self.email, self.name, self.month, self.year]):
            print('Make sure you have specified email, name, month and year')
            self.email = None
