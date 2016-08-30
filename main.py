#!/usr/bin/python3

""" Main function """

import config_options
import get_emails
import re
import sys


def print_email(count, date, subject):
    # Differentiate between nonexistent mailing list and no found emails
    if count == 1:
        print ('{0:>8} {1} {2}'.format(' ', date, subject))
    else:
        print ('{0:>8} {1} {2}'.format(str(count).join(("[", "]")), date, subject))

def main():
    """
    Parse configuration file and command line options - use either command
    line options or configuration file. If insufficient options are provided
    on command line, configuration file is used as fallback.

    Gather lists of all sent mails for given user during specified time and
    print them.
    """
    #options = config_options.Options(sys.argv[1:])
    # Email is set only if all needed options are specified
    #if options.email is None or \
    #   options.name is None:
    #    if len(sys.argv) > 1:
    #        print('Falling back to configuration file')
        # Needed options in command are missing, use config
    options = config_options.Config(sys.argv[1:])
    if options.email is None or \
       options.name is None or \
       options.year is None or \
       options.month is None:
        return

    print('Searching for {0} <{1}>'.format(options.name, str(options.email).strip('[]')), file=sys.stderr)
    # Ths dict's structure is {message-id: (subject, date)}
    emails = {}
    if options.lkml:
        emails.update(get_emails.LKML(options, "lkml").emails)
    for url, mailing_lists in options.pipermail.items():
        for mailing_list in mailing_lists:
            emails.update(get_emails.Pipermail(options, url, mailing_list).emails)
    for url, mailing_lists in options.hyperkitty.items():
        for mailing_list in mailing_lists:
            emails.update(get_emails.HyperKitty(options, url, mailing_list).emails)
    for mailing_list in options.spinics:
        emails.update(get_emails.Spinics(options, mailing_list).emails)

    emails = [info for message_id, info in emails.items()]
    patched, replied  = [], []
    patched_count, replied_count = 0, 0
    filtered_emails = {}
    print('Messages:')
    for subject, date in emails:
        if subject in filtered_emails:
            filtered_emails[subject][1] += 1
        else:
            filtered_emails[subject] = [date, 1]
    filtered_emails = [(count, date, subject) for subject, (date, count) in filtered_emails.items()]
    filtered_emails.sort(key=lambda tup: tup[1])
    for count, date, subject in filtered_emails:
        print_email(count, date, subject)
        if re.match('^re:.*|.*\sre:\s.*', subject, re.IGNORECASE):
            replied.append((count, date, subject))
            replied_count += count
        elif re.match('.*\Wpatch\W.*', subject, re.IGNORECASE):
            patched.append((count, date, subject))
            patched_count += count
    print('Patches:')
    for count, date, subject in patched:
        print_email(count, date, subject)
    print('Replied:')
    for count, date, subject in replied:
        print_email(count, date, subject)
    print('{0} message(s) found, {1} patched, {2} replied'.format(len(emails), patched_count, replied_count))

if __name__ == '__main__':
    main()
