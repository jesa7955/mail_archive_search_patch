#!/usr/bin/python3

""" Main function """

import config_options
import get_emails
import sys


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
        print('{0} messages found in LKML'.format(len(lkml.emails)))
        for message in lkml.emails:
            print(4 * ' ' + message)
    print()
    for mailing_list in options.rh_internal:
        mails = get_emails.RHInternal(options, mailing_list)
        if mails.emails is not None:
            print('{0} messages found in {1}'.format(len(mails.emails),
                                                     mailing_list))
            for message in mails.emails:
                print(4 * ' ' + message.decode('utf-8'))
        print()


if __name__ == '__main__':
    main()
