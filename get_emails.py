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
    """ Class for retrieving from another archiver of LKML """
    url_base = 'http://lkml.iu.edu/hypermail/linux/kernel/'

    def _retrieve(self, options, list_name=None):

        patterns = []
        for email in options.email:
            email_user, email_domain = re.split('@', email)
            patterns.append('{0} &lt;{1}@{2}&gt;'.format(options.name, email_user, 'x' * len(email_domain)))
        week_id = 0
        while True:
            url = '{0}{1}{2}.{3}/author.html'.format(self.url_base,
                                                     options.year % 100,
                                                     str(options.month).zfill(2),
                                                     week_id)
            try:
                lines = urllib.request.urlopen(url).readlines()
            except urllib.error.HTTPError:
                return
            threads = []
            for index, line in enumerate(lines):
                if options.name.encode('utf-8') in line:
                    for index2, line2 in enumerate(lines[index + 1:]):
                        if re.match(b'<li><strong>.*</strong>$', line2):
                            threads = lines[index + 1: index + index2 + 1]
                            break
                    break
            for thread in threads:
                item = re.split('[<>]', thread.decode('utf-8'))
                subject, date = item[8], dateparser.parse(item[14]).date()
                detail_url = '{0}{1}'.format(url[:-len('author.html')],
                                              item[7].split()[-1].split("=")[-1].strip('"'))
                detail_lines = urllib.request.urlopen(detail_url).read().decode('utf-8').split("\n")
                for line in detail_lines:
                    if 'X-Message-Id:' in line:
                        message_id = line[len('<!--X-Message-Id: '):-len(' -->')].replace('&#45;', '-')
                    if any(match in line for match in patterns):
                        self.emails[message_id] = (subject, str(date))
                        break
            week_id += 1

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
