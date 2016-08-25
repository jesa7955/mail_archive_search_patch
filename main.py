#!/usr/bin/python3

""" Main function """

import config_options
import get_emails
import re
import sys


def print_list(mails, list_name):
    # Differentiate between nonexistent mailing list and no found emails
    if mails.emails:
        print('{0} messages found in {1}'.format(len(mails.emails), list_name))
        for message, date in mails.emails:
            print('    {0}: {1}'.format(date, message))
        print()

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

    #if options.lkml:
    #    print_list(get_emails.LKML(options), 'LKML')
    #for mailing_list in options.rh_internal:
    #    print_list(get_emails.RHInternal(options, mailing_list), mailing_list)
    #for mailing_list in options.pipermail:
    #    print_list(get_emails.Pipermail(options, mailing_list), mailing_list)
    #for mailing_list in options.hyperkitty:
    #    print_list(get_emails.HyperKitty(options, mailing_list), mailing_list)
    #for mailing_list in options.spinics:
    #    print_list(get_emails.Spinics(options, mailing_list), mailing_list)
    emails = {}
    if options.lkml:
        emails.update(get_emails.LKML(options).emails)
    for mailing_list in options.rh_internal:
        emails.update(get_emails.RHInternal(options, mailing_list).emails)
    for mailing_list in options.pipermail:
        emails.update(get_emails.Pipermail(options, mailing_list).emails)
    for mailing_list in options.hyperkitty:
        emails.update(get_emails.HyperKitty(options, mailing_list).emails)
    for mailing_list in options.spinics:
        emails.update(get_emails.Spinics(options, mailing_list).emails)

    emails = [info for message_id, info in emails.items()]
    emails.sort(key=lambda tup: tup[1])
    print('{0} message(s) found'.format(len(emails)))
    patched = []
    replyed = []
    for message, date in emails:
        print('    {0}: {1}'.format(date, message))
        if re.match('.*re:.*', message, re.IGNORECASE):
            replyed.append((date, message))
        elif re.match('.*\Wpatch\W.*', message, re.IGNORECASE):
            patched.append((date, message))
    print('{0} patched'.format(len(patched)))
    for date, message in patched:
        print('    {0}: {1}'.format(date, message))
    print('{0} replyed'.format(len(replyed)))
    for date, message in replyed:
        print('    {0}: {1}'.format(date, message))

if __name__ == '__main__':
    main()
