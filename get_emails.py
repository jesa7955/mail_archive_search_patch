""" Retrieving emails from mailing list archives """

import calendar
import datetime
import gzip
import io
import mailbox
import re
import sys
import urllib.request
import dateparser
from html.parser import HTMLParser


class mboxFromFile(mailbox.mbox):
    """ Custom class for reading mbox from file object instead of path. """
    def __init__(self, content, factory=None, create=True):
        self._message_factory = mailbox.mboxMessage
        self._file = content
        self._toc = None
        self._next_key = 0
        self._pending = False
        self._pending_sync = False
        self._locked = False
        self._file_length = None
        self._factory = factory


class SpinicsHTMLParser(HTMLParser):
    in_li = False
    inner_li = False
    has_attrs = False
    thread_list = []
    cur = {}
    def handle_starttag(self, tag, attrs):
        if tag == 'li':
            if not self.in_li:
                self.in_li = True
            else:
                self.inner_li = True
        elif tag == 'a' and self.in_li and len(attrs) > 1:
            self.has_attrs = True
            self.cur = {}
            self.cur['attrs'] = attrs
        elif tag == 'html':
            self.thread_list = []

    def handle_endtag(self, tag):
        if tag == 'li':
            if self.inner_li:
                self.inner_li = False
            else:
                self.in_li = False
                self.has_attrs = False

    def handle_data(self, data):
        if self.in_li:
            if self.inner_li and data != "From":
                self.cur['email'] = data.strip(": ")
                self.thread_list.append(self.cur)
            elif data != "From" and not data.isspace() and self.has_attrs:
                self.cur['subject'] = data


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
    over = False
    parser = SpinicsHTMLParser()

    def _retrieve(self, options, list_name=None):
        # Pattern is the same as LKML's one
        patterns = []
        for email in options.email:
            email_user, email_domain = re.split('@', email)
            patterns.append('{0} <{1}@{2}>'.format(
                options.name, email_user, 'x' * len(email_domain)))
        # The range of the dates we want to search
        first_day = datetime.date(options.year, options.month, 1)
        if options.month == 12:
            last_day = datetime.date(options.year+1, 1, 1)
        else:
            last_day = datetime.date(options.year, options.month + 1, 1)
        date_range = (first_day, last_day)
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
            if type(page) != tuple and not self.over:
                page = page.read()
                self._search_in_page(page, list_name, patterns, date_range)
            else:
                break
            url_id += 1

    def _search_in_page(self, page, list_name, patterns, date_range):
        self.parser.feed(page.decode())
        thread_list = self.parser.thread_list
        for thread in thread_list:
            if any([match in thread['email'] for match in patterns]):
                subject = thread['subject']
                herf = thread['attrs'][1][1]
                detail_url = '{0}{1}/{2}'.format(self.url_base,
                                                 list_name,
                                                 herf)

                detail_page = self._fetch_url(detail_url)
                if type(detail_page) != tuple:
                    detail_lines = detail_page.read().split(b'\n')
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
                                    return
                        elif b'X-Message-Id:' in line:
                            m_id_start = len('<!--X-Message-Id: ')
                            m_id_end = -len(' -->')
                            message_id = line.decode('utf-8')[m_id_start:m_id_end]
                            # This HTML pages use &#45 instead of -
                            message_id = message_id.replace('&#45;', '-')
                        elif message_id and date and date < date_range[1]:
                            self.emails[message_id] = (subject, str(date))

class GzipArchived(GeneralList):
    """
    Base class for lists which provide downloadable gziped archvie files
    """
    def __init__(self, options, url=None, list_name=None, debug=False,
                 timeout=10):
        if url is not None:
            self.url_base = url
        super().__init__(options, list_name, debug, timeout)

    def _beautify_string(self, string):
        if string is not None:
            return ' '.join(string.split()).strip("<>")
        return None

    def _parse_gz_archive(self, url, options):
        """ Method used to parse information from gziped archive """
        gz_archive = self._fetch_url(url)
        if type(gz_archive) != tuple:
            gz_file = gzip.GzipFile(fileobj=io.BytesIO(gz_archive.read()))
            box = mboxFromFile(gz_file)
        else:
            return
        # Some archiver stores email address as "foo at bar.com" format
        # Examples kexec upstream and kexec-fedora
        patterns = [email for email in options.email] + \
                   [email.replace("@", " at ")
                    for email in options.email]
        for message in box:
            if any(match in message['from'] for match in patterns):
                subject = self._beautify_string(message['subject'])
                message_id = self._beautify_string(message['message-id'])
                in_reply_to = self._beautify_string(message['in-reply-to'])
                date_info = message['date']
                lines = message.as_string().split("\n")
                patch_start = [
                        start_index for start_index, start_line in
                        enumerate(lines) if re.match('^--- .*', start_line)]
                patch_included = False
                for p_start in patch_start:
                    if p_start + 2 < len(lines):
                        s_line = re.match('^\+\+\+ .*',
                                lines[p_start + 1])
                        t_line = re.match('^@@ .*',
                                lines[p_start + 2])
                        patch_included = \
                                s_line is not None and \
                                t_line is not None
                re_included = re.match('^re:.*|.*\sre:\s.*',
                                       subject,
                                       re.IGNORECASE)
                if in_reply_to and \
                   not re_included and \
                   not patch_included:
                    subject = 'Re: ' + subject
                date = dateparser.parse(date_info)
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
