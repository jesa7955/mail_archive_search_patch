#!/usr/bin/python3

""" Main function """

import config_options
import get_emails
import re
import sys


def print_email(count, date, subject):
    if count == 1:
        print('{0:>8} {1} {2}'.format(' ', date, subject))
    else:
        print('{0:>8} {1} {2}'.format(
            str(count).join(("[", "]")), date, subject))


def main():
    """
    Parse configuration file and command line options - use either command
    line options or configuration file. If insufficient options are provided
    on command line, configuration file is used as fallback.

    Gather lists of all sent mails for given user during specified time and
    print them.
    """

    # Parse options from both configuration file and command line
    options = config_options.Config(sys.argv[1:])
    if options.email is None or \
       options.name is None or \
       options.year is None or \
       options.month is None:
        return
    # Start searching
    searching_email = ' '.join(
            '<' + email.strip("'") + '>' for email in options.email)
    print('Searching for {} {}'.format(
        options.name, searching_email), file=sys.stderr)
    # Ths dict's structure is {message-id: (subject, date)}
    emails = {}
    if options.lkml:
        emails.update(get_emails.LKML(options, "lkml",
                                      debug=options.debug).emails)
    for url, mailing_lists in options.pipermail.items():
        for mailing_list in mailing_lists:
            emails.update(get_emails.Pipermail(
                options, url, mailing_list, debug=options.debug).emails)
    for url, mailing_lists in options.hyperkitty.items():
        for mailing_list in mailing_lists:
            emails.update(get_emails.HyperKitty(
                options, url, mailing_list, debug=options.debug).emails)
    for mailing_list in options.spinics:
        emails.update(get_emails.Spinics(
            options, mailing_list, debug=options.debug).emails)
    emails = [info for message_id, info in emails.items()]
    patched, replied, others = [], [], []
    patched_count, replied_count, others_count = 0, 0, 0
    # Count emails which have the same subject
    filtered_emails = {}
    for subject, date in emails:
        if subject in filtered_emails:
            if date > filtered_emails[subject][0]:
                filtered_emails[subject][0] = date
            filtered_emails[subject][1] += 1
        else:
            filtered_emails[subject] = [date, 1]
    filtered_emails = [
            (count, date, subject) for subject, (date, count) in
            filtered_emails.items()]
    filtered_emails.sort(key=lambda tup: tup[1])
    # Output result
    for count, date, subject in filtered_emails:
        if re.match('^re:.*|.*\sre:\s.*', subject, re.IGNORECASE):
            replied.append((count, date, subject))
            replied_count += count
        elif re.match('.*\Wpatch\W.*', subject, re.IGNORECASE):
            if re.match('.*\s0+\/\d.*', subject, re.IGNORECASE):
                others.append((count, date, subject))
                others_count += count
            else:
                patched.append((count, date, subject))
                patched_count += count
        else:
            others.append((count, date, subject))
            others_count += count
    print('Patches:')
    for count, date, subject in patched:
        print_email(count, date, subject)
    print('Replied:')
    for count, date, subject in replied:
        print_email(count, date, subject)
    print('Others:')
    for count, date, subject in others:
        print_email(count, date, subject)
    print("{} meesages found, {} patches, {} replied, {} others".format(
                        len(emails), patched_count,
                        replied_count, others_count))

if __name__ == '__main__':
    main()
