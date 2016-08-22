""" Configuration file and options parsing """

import argparse
import configparser
import os

CONFIG = os.path.expanduser("~/.list_archive")


class GeneralConfig(object):
    """ General option class """
    def __init__(self, arguments=None):
        self.parser = None
        self.name = None
        self.email = None
        self.lkml = None
        self.rh_internal = None
        self.pipermail = None
        self.hyperkitty = None
        self.spinics = None
        self.month = None
        self.year = None
        self._get_options(arguments)

    def _get_options(self, arguments=None):
        raise NotImplementedError

class Config(GeneralConfig):
    """ Parse configuration file if command options are missing """
    def _get_options(self, arguments=None):
        self.parser = configparser.ConfigParser()

        try:
            self.parser.read_file(open(CONFIG))
            self.month = int(self.parser['general']['month'])
            self.year = int(self.parser['general']['year'])
            self.name = self.parser['general']['name']
            self.email = [mail.strip() for mail in
                          self.parser['general']['email'].split(',')]
        except FileNotFoundError:
            print('Configuration file {0} not found'.format(CONFIG))
        except KeyError as key_not_found:
            print('{0} not configured in {1}'.format(key_not_found, CONFIG))
        self.lkml = 'LKML' in self.parser.sections()
        try:
            self.rh_internal = [mailing_list.strip() for mailing_list in
                                self.parser['RH']['lists'].split(',')]
        except KeyError:
            self.rh_internal = []

class Options(GeneralConfig):
    """ Parse command line options """
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
