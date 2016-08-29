""" Retrieving emails from mailing list archives """

import calendar
import datetime
import gzip
import re
import sys
import urllib.request
import dateparser


class GeneralList(object):
    """ General list class """

    def __init__(self, options, list_name=None):
        self.emails = {}
        print("Search {0} From {1}".format(list_name, self.url_base), file=sys.stderr)
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

class Spinics(GeneralList):
    """ Class for retrieving emails from www.spinics.com """
    url_base = 'http://www.spinics.net/lists/'

    def _retrieve(self, options, list_name=None):
        self.over = False
        # Email pattern
        patterns = []
        for email in options.email:
            email_user, email_domain = re.split('@', email)
            patterns.append('{0} &lt;{1}@{2}&gt;'.format(options.name, email_user, 'x' * len(email_domain)))
        # The range of the dates we want to search
        date_range = [day for day in calendar.Calendar().itermonthdates(options.year, options.month)
                     if day.month == options.month]
        # Search for match in the first page
        first_url = '{0}{1}/maillist.html'.format(self.url_base,
                                                     list_name,)
        try:
            page = urllib.request.urlopen(first_url).read()
            self._search_in_page(page, list_name, patterns, date_range)
        except urllib.error.HTTPError:
            print('URL {0} does not exist'.format(first_url))
            self.emails = None
            return

        # Search in the rest ones
        url_id = 2
        while True:
            iterate_url = '{0}{1}/mail{2}.html'.format(self.url_base,
                                                       list_name,
                                                       url_id)
            try:
                page = urllib.request.urlopen(iterate_url).read()
                if not self.over:
                    self._search_in_page(page, list_name, patterns, date_range)
            except urllib.error.HTTPError:
                break
            url_id += 1

    def _search_in_page(self, page, list_name, patterns, date_range):
        lines = page.split(b'<li><strong>')
        # Magic number stores infomation we need
        for line in lines[1:]:
            item = re.split('[<>]', line.decode('utf-8'))
            if any(match in item[14] for match in patterns):
                subject = item[2]
                detail_url = '{0}{1}/{2}'.format(self.url_base,
                                               list_name,
                                               item[1].split()[2].split('=')[1].replace('"', ''))

                detail_lines = urllib.request.urlopen(detail_url).read().split(b'\n')
                message_id, date = None, None
                for line in detail_lines:
                    if b'X-Date:' in line:
                        date = dateparser.parse(line.decode('utf-8')[len('<!--X-Date: '):-len(' -->')].replace('&#45;', '-')).date()
                        if date < date_range[0]:
                            self.over = True
                    elif b'X-Message-Id:' in line:
                        message_id = line.decode('utf-8')[len('<!--X-Message-Id: '):-len(' -->')].replace('&#45;', '-')
                    elif message_id and date and not self.over:
                        self.emails[message_id] = (subject, str(date))
                        return
                    elif self.over:
                        return

class GzipArchived(GeneralList):
    """ Base class for lists which provide downloadable gziped archive files """
    def __init__(self, options, url=None, list_name=None):
        if url is not None:
            self.url_base = url
        super().__init__(options, list_name)

    def _parse_gz_archive(self, url, options):
        try:
            with urllib.request.urlopen(url) as gz_archive:
                with gzip.open(gz_archive, 'r') as gz_file:
                    lines = [line for line in gz_file.read().split(b'\n')]
        except urllib.error.HTTPError:
            print('URL {0} does not exist'.format(url))
            self.emails = None
            return
        # Some archiver stores email address as "foo at bar.com" format
        patterns  = [b'From ' + email.encode('utf-8')
                     for email in options.email] + \
                    [b'From ' + email.replace('@', ' at ').encode('utf-8')
                     for email in options.email]
        for index, line in enumerate(lines):
            if any(match in line for match in patterns):
                subject_start = None
                for index2, line2 in enumerate(lines[index + 1:]):
                    if b'Subject: ' in line2:
                        subject_start = index2
                    elif re.match(b'^.*:.*', line2) and subject_start:
                        subject_end = index2
                        subject = b' '.join(item.strip() for item in lines[index + 1:][subject_start:subject_end]).\
                                                                                  decode('utf-8')[len('Subject: '):]
                        break
                for index2, line2 in enumerate(lines[index + 1:]):
                    if re.match(b'^From .*', line2):
                        in_reply_to = [next_line for next_line in lines[index + 1:index + 1 + index2]
                                       if re.match(b'^In-Reply-To: .*', next_line)]
                        patch_start = [start_index for start_index, start_line in enumerate(lines[index + 1:index + 1 + index2])
                                                       if re.match(b'^--- .*', start_line)]
                        patch_included = False
                        for start_index in patch_start:
                            patch_included = re.match(b'^\+\+\+ .*', lines[index + 1 + start_index + 1]) is not None and \
                                             re.match(b'^@@ .*', lines[index + 1 + start_index + 2]) is not None
                        if len(in_reply_to) != 0 and \
                            not re.match('.*re:.*', subject, re.IGNORECASE) and \
                            not patch_included:
                            subject = 'Re: ' + subject
                        break
                message_id = next(next_line[len(b'Message-ID: '):].decode('utf-8').strip('<>')
                                  for next_line in lines[index + 1:]
                                  if b'Message-ID: ' in next_line)
                date_info = next(next_line[len(b'Date: '):].decode('utf-8')
                           for next_line in lines[index + 1:]
                           if b'Date: ' in next_line)
                if date_info.find('(') != -1:
                    date_info = date_info[:date_info.find('(') - 1]
                date = dateparser.parse(date_info)
                if date:
                    date = date.date()
                self.emails[message_id] = (subject, str(date))

class RHInternal(GzipArchived):
    """ Class for retrieving emails from internal Red Hat lists """
    url_base = 'http://post-office.corp.redhat.com/archives/'

    def _retrieve(self, options, list_name=None):
        # RH mailing list archives use full month name
        month = datetime.date(options.year, options.month, 1).strftime('%B')
        url = '{0}{1}/{2}-{3}.txt.gz'.format(self.url_base,
                                             list_name,
                                             options.year,
                                             month)
        super()._parse_gz_archive(url, options)

class Pipermail(GzipArchived):
    """ Class for retrieving emails from pipermail, default archiver of mailman 2 """
    url_base = 'http://lists.infradead.org/pipermail/'

    def _retrieve(self, options, list_name=None):
        # Pipermail uses the same format as RHInternal archiver
        month = datetime.date(options.year, options.month, 1).strftime('%B')
        url = '{0}{1}/{2}-{3}.txt.gz'.format(self.url_base,
                                           list_name,
                                           options.year,
                                           month)
        super()._parse_gz_archive(url, options)

class HyperKitty(GzipArchived):
    """ Class for retrieving emails from HyperKitty, default archiver of mailman 3 """
    url_base = 'https://lists.fedoraproject.org/archives/'

    def _retrieve(self, options, list_name=None):
        # Basic method is the same as pipermail and rh-internal
        domain = self.url_base.split('/')[2]
        month = str(options.month).zfill(2)
        next_month = str(options.month + 1).zfill(2)
        # Example: https://lists.fedoraproject.org/archives/list/kexec@lists.fedoraproject.org/export/kexec@lists.fedoraproject.org-2016-01.mbox.gz?start=2016-01-01&end=2016-02-01
        url = '{0}list/{1}@{2}/export/{1}@{2}-{3}-{4}.mbox.gz?start={3}-{4}-01&end={3}-{5}-01'.format(self.url_base,
                                                                                                      list_name,
                                                                                                      domain,
                                                                                                      options.year,
                                                                                                      month,
                                                                                                      next_month)
        super()._parse_gz_archive(url, options)
