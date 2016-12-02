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

    def __init__(self, options, list_name=None, debug=False, timeout=10):
        self.emails = {}
        print("Searching {0} From {1}".format(
            list_name, self.url_base), file=sys.stderr)
        self._debug = debug
        self._timeout = timeout
        self._retrieve(options, list_name)

    def _retrieve(self, options, list_name=None):
        raise NotImplementedError

    def _fetch_url(self, url):
        if self._debug:
            print("Fetching {}".format(url), file=sys.stderr)
        try:
            return urllib.request.urlopen(url, timeout=self._timeout)
        except urllib.error.HTTPError:
            if self._debug:
                print("{} is not found".format(url), file=sys.stderr)
            return (None, "not_found")
        except urllib.error.URLError:
            print("{} is not accessable".format(url), file=sys.stderr)
            return (None, 'unaccessable')


class LKML(GeneralList):
    """ Class for retrieving from another archiver of LKML """
    url_base = 'http://lkml.iu.edu/hypermail/linux/kernel/'

    def _retrieve(self, options, list_name=None):

        # Pattern is like Name &lt;foo@xxxxxxx&gt;
        patterns = []
        for email in options.email:
            email_user, email_domain = re.split('@', email)
            patterns.append('{0} &lt;{1}@{2}&gt;'.format(
                options.name, email_user, 'x' * len(email_domain)))
        # This archiver stores emails in week-based period
        week_id = -1
        first_day = datetime.date(options.year, options.month, 1)
        last_day = datetime.date(options.year, (options.month + 1) % 12, 1)
        if options.month == 12:
            last_day = datetime.date(options.year+1, 1, 1)
        else:
            last_day = datetime.date(options.year, options.month + 1, 1)
        while True:
            week_id += 1
            url = '{0}{1}{2}.{3}/author.html'.format(
                    self.url_base,
                    options.year % 100,
                    str(options.month).zfill(2),
                    week_id)
            page = self._fetch_url(url)
            if type(page) == tuple:
                if page[1] == 'not_found':
                    return
                else:
                    continue
            lines = page.readlines()
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
                if date < first_day or date >= last_day:
                    continue
                detail_url = '{0}{1}'.format(
                        url[:-len('author.html')],
                        item[7].split()[-1].split("=")[-1].strip('"'))
                d_page = self._fetch_url(detail_url)
                if type(d_page) != tuple:
                    detail_lines = d_page.read().decode('utf-8').split("\n")
                else:
                    continue
                for line in detail_lines:
                    if 'X-Message-Id:' in line:
                        m_id_start = len('<!--X-Message-Id: ')
                        m_id_end = -len(' -->')  # Reversed index
                        m_id_info = line[m_id_start:m_id_end]
                        message_id = m_id_info.replace('&#45;', '-')
                    if any(match in line for match in patterns):
                        self.emails[message_id] = (subject, str(date))
                        break


class Spinics(GeneralList):
    """ Class for retrieving emails from www.spinics.com """
    url_base = 'http://www.spinics.net/lists/'

    def _retrieve(self, options, list_name=None):
        self.over = False
        # Pattern is the same as LKML's one
        patterns = []
        for email in options.email:
            email_user, email_domain = re.split('@', email)
            patterns.append('{0} &lt;{1}@{2}&gt;'.format(
                options.name, email_user, 'x' * len(email_domain)))
        # The range of the dates we want to search
        date_range = [
                day for day in
                calendar.Calendar().itermonthdates(options.year, options.month)
                if day.month == options.month]
        # Search for match in the first page
        first_url = '{0}{1}/maillist.html'.format(self.url_base,
                                                  list_name,)
        page = self._fetch_url(first_url)
        if type(page) != tuple:
            page = page.read()
            self._search_in_page(page, list_name, patterns, date_range)
        elif page[1] == 'not_found':
            return

        # Search in the rest ones
        url_id = 2
        while True:
            current_url = '{0}{1}/mail{2}.html'.format(self.url_base,
                                                       list_name,
                                                       url_id)
            page = self._fetch_url(current_url)
            if type(page) != tuple:
                page = page.read()
                if not self.over:
                    self._search_in_page(page, list_name, patterns, date_range)
            else:
                break
            url_id += 1

    def _search_in_page(self, page, list_name, patterns, date_range):
        lines = page.split(b'<li><strong>')
        # Magic index point to the member which stores infomation we need
        for line in lines[1:]:
            item = re.split('[<>]', line.decode('utf-8'))
            if any(match in item[14] for match in patterns):
                subject = item[2]
                herf = item[1].split()[2].split('=')[1].replace('"', '')
                detail_url = '{0}{1}/{2}'.format(self.url_base,
                                                 list_name,
                                                 herf)

                detail_page = self._fetch_url(detail_url)
                if type(detail_page) != tuple:
                    detail_lines = detail_page.read().split(b'\n')
                else:
                    continue
                message_id, date = None, None
                for line in detail_lines:
                    if b'X-Date:' in line:
                        d_start = len('<!--X-Date: ')
                        d_end = -len(' -->')
                        d_info = line.decode('utf-8')[d_start:d_end]
                        date = dateparser.parse(d_info.replace('&#45;', '-'))
                        if date is not None:
                            date = date.date()
                        if date < date_range[0]:
                            self.over = True
                    elif b'X-Message-Id:' in line:
                        m_id_start = len('<!--X-Message-Id: ')
                        m_id_end = -len(' -->')
                        message_id = line.decode('utf-8')[m_id_start:m_id_end]
                        # This HTML pages use &#45 instead of -
                        message_id = message_id.replace('&#45;', '-')
                    elif message_id and date and not self.over:
                        self.emails[message_id] = (subject, str(date))
                        return
                    elif self.over:
                        return


class GzipArchived(GeneralList):
    """
    Base class for lists which provide downloadable gziped archvie files
    """
    def __init__(self, options, url=None, list_name=None, debug=False,
                 timeout=10):
        if url is not None:
            self.url_base = url
        super().__init__(options, list_name, debug, timeout)

    def _parse_gz_archive(self, url, options):
        """ Method used to parse information from gziped archive """
        gz_archive = self._fetch_url(url)
        if type(gz_archive) != tuple:
            with gzip.open(gz_archive, 'r') as gz_file:
                lines = [line for line in gz_file.read().split(b'\n')]
        else:
            return
        # Some archiver stores email address as "foo at bar.com" format
        # Examples kexec upstream and kexec-fedora
        patterns = [b'From ' + email.encode('utf-8')
                    for email in options.email] + \
                   [b'From ' + email.replace('@', ' at ').encode('utf-8')
                    for email in options.email]
        for index, line in enumerate(lines):
            if any(match in line for match in patterns):
                # Sometimes a subject may be splited into multiple lines
                subject_start, subject_end = None, None
                for index2, line2 in enumerate(lines[index + 1:]):
                    if re.match(b'^Subject: .*', line2) and \
                       subject_end is None:
                        subject_start = index2
                    elif re.match(b'^\S*:\s.*', line2) and \
                            subject_start is not None:
                        subject_end = index2
                        subject = b' '.join(
                                item.strip() for item in
                                lines[index + 1:][subject_start:subject_end])
                        subject = subject.decode('utf-8')[len('Subject: '):]
                        subject_start = None
                    elif re.match(b'^From\s.*', line2) or \
                            index2 == len(lines[index + 1:]) - 1:
                        in_reply_to = False
                        for next_line in lines[index + 1:index + 1 + index2]:
                            if re.match(b'^In-Reply-To: .*',
                                        next_line,
                                        re.IGNORECASE):
                                in_reply_to = True
                            if re.match(b'^Message-ID: .*',
                                        next_line,
                                        re.IGNORECASE):
                                message_id = next_line[len(b'Message-ID: '):]
                                message_id = message_id.decode().strip('<>')
                            elif re.match(b'^Date: .*',
                                          next_line,
                                          re.IGNORECASE):
                                date_info = next_line[len(b'Date: '):].decode()
                        # Confirm whether there is a patch included
                        patch_start = [
                                start_index for start_index, start_line in
                                enumerate(lines[index + 1:index + 1 + index2])
                                if re.match(b'^--- .*', start_line)]
                        patch_included = False
                        for p_start in patch_start:
                            if index + 1 + p_start + 2 < len(lines):
                                s_line = re.match(b'^\+\+\+ .*',
                                                  lines[index + 1 +
                                                        p_start + 1])
                                t_line = re.match(b'^@@ .*',
                                                  lines[index + 1 +
                                                        p_start + 2])
                                patch_included = \
                                    s_line is not None and \
                                    t_line is not None or \
                                    patch_included
                        # Some archives don't include 'Re:' for replies
                        re_included = re.match('^re:.*|.*\sre:\s.*',
                                               subject,
                                               re.IGNORECASE)
                        if in_reply_to and \
                           not re_included and \
                           not patch_included:
                            subject = 'Re: ' + subject
                        break
                # dateparser can't parse date like '2016, Aug, 28, -0500 (EST)'
                if date_info.find('(') != -1:
                    date_info = date_info[:date_info.find('(') - 1]
                date = dateparser.parse(date_info)
                # In case we got a date_info which dateparser can't parse
                if date:
                    date = date.date()
                self.emails[message_id] = (subject, str(date))


class RHInternal(GzipArchived):
    """ Class for retrieving emails from internal Red Hat lists(deprecated) """
    url_base = 'http://post-office.corp.redhat.com/archives/'

    def _retrieve(self, options, list_name=None):
        # RH mailing list archives use full month name
        month = datetime.date(options.year, options.month, 1).strftime('%B')
        url = '{0}{1}/{2}-{3}.txt.gz'.format(self.url_base,
                                             list_name,
                                             options.year,
                                             month)
        self._parse_gz_archive(url, options)


class Pipermail(GzipArchived):
    """
    Class for retrieving emails from pipermail, default archiver of mailman 2
    """
    url_base = 'http://lists.infradead.org/pipermail/'

    def _retrieve(self, options, list_name=None):
        # Pipermail uses the same format as RHInternal archiver
        month = datetime.date(options.year, options.month, 1).strftime('%B')
        url = '{0}{1}/{2}-{3}.txt.gz'.format(self.url_base,
                                             list_name,
                                             options.year,
                                             month)
        self._parse_gz_archive(url, options)


class HyperKitty(GzipArchived):
    """
    Class for retrieving emails from HyperKitty, default archiver of mailman 3
    """
    url_base = 'https://lists.fedoraproject.org/archives/'

    def _retrieve(self, options, list_name=None):
        # Basic method is the same as pipermail and rh-internal
        domain = self.url_base.split('/')[2]
        month = str(options.month).zfill(2)
        next_month = str(options.month + 1).zfill(2)
        url = ("{0}list/{1}@{2}/export/{1}@{2}-{3}-{4}.mbox.gz?"
               "start={3}-{4}-01&end={3}-{5}-01").format(self.url_base,
                                                         list_name,
                                                         domain,
                                                         options.year,
                                                         month,
                                                         next_month)
        self._parse_gz_archive(url, options)
