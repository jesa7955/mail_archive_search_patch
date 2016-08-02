#!/usr/bin/python3

""" Main function """

import config_options
import get_emails
import sys


def print_list(mails, list_name):
    print('{0} messages found in {1}'.format(len(mails.emails), list_name))
    for message, date in mails.emails:
        print('    {0}: {1}'.format(date, message))


def main():
    """
    Parse configuration file and command line options - use either command
    line options or configuration file. If insufficient options are provided
    on command line, configuration file is used as fallback.

    Gather lists of all sent mails for given user during specified time and
    print them.
    """
    options = config_options.Options(sys.argv[1:])
    # Email is set only if all needed options are specified
    if options.email is None:
        if len(sys.argv) > 1:
            print('Falling back to configuration file')
        # Needed options in command are missing, use config
        options = config_options.Config()
        if options.email is None:
            return

    if options.lkml:
        lkml = get_emails.LKML(options)
        print_list(lkml, 'LKML')
    print()
    for mailing_list in options.rh_internal:
        mails = get_emails.RHInternal(options, mailing_list)
        if mails.emails is not None:
            print_list(mails, mailing_list)
        print()


if __name__ == '__main__':
    main()
