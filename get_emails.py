""" Retrieving emails from mailing list archives """

import calendar
import datetime
import gzip
import re
import urllib.request


class GeneralList(object):
    """ General list class """

    def __init__(self, options, list_name=None):
        self.emails = []
        self._retrieve(options, list_name)

    def _retrieve(self, options, list_name=None):
        raise NotImplementedError


class LKML(GeneralList):
    """ Class for retrieving emails from LKML """
    url_base = 'https://lkml.org/lkml/'

    def _retrieve(self, options, list_name=None):
        url = '{0}{1}/{2}/'.format(self.url_base, options.year, options.month)
        for day in range(1,
                         calendar.monthrange(options.year,
                                             options.month)[1] + 1):
            # Need to specify known User-Agent header because of bot protection
            req = urllib.request.Request('{0}{1}'.format(url, day),
                                         headers={'User-Agent': 'Mozilla/5.0'})
            page = urllib.request.urlopen(req).read().decode('utf-8')
            table = [row for row in page.split('<tr class=')]
            for row in table[1:]:
                columns = [column for column in
                           row.split('/lkml/{0}/{1}/{2}'.format(options.year,
                                                                options.month,
                                                                day))]
                if options.name in columns[2]:
                    self.emails.append((re.split('[><]', columns[1])[1],
                                        '{0}.{1}.{2}'.format(day,
                                                             options.month,
                                                             options.year)))


class RHInternal(GeneralList):
    """ Class for retrieving emails from internal Red Hat lists """
    url_base = 'http://post-office.corp.redhat.com/archives/'

    def _retrieve(self, options, list_name=None):
        # RH mailing list archives use full month name
        month = datetime.date(options.year, options.month, 1).strftime('%B')
        url = '{0}{1}/{2}-{3}.txt.gz'.format(self.url_base,
                                             list_name,
                                             options.year,
                                             month)
        try:
            with urllib.request.urlopen(url) as gz_archive:
                with gzip.open(gz_archive, 'r') as gz_file:
                    lines = [line for line in gz_file.read().split(b'\n')]
        except urllib.error.HTTPError:
            print('URL {0} does not exist'.format(url))
            self.emails = None
            return
        patterns = [b'From ' + email.encode('utf-8')
                    for email in options.email]
        for index, line in enumerate(lines):
            if any(match in line for match in patterns):
                subject = next(next_line[len('Subject: '):].decode('utf-8')
                               for next_line in lines[index + 1:]
                               if b'Subject: ' in next_line)
                day = next(next_line[len('Date: day, '):].decode(
                    'utf-8').split(' ')[0]
                           for next_line in lines[index + 1:]
                           if b'Date: ' in next_line)
                date = '{0}.{1}.{2}'.format(day, options.month, options.year)
                self.emails.append((subject, date))
