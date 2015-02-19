#!/usr/bin/env python

"""
The MIT License (MIT)

Copyright (c) 2015 Raj Perera <rajiteh@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import requests
import requests_cache
import logging
import re
import sys
import icalendar
import json
from pprint import pprint
from bs4 import BeautifulSoup
from urllib import urlencode, quote
from datetime import datetime

class YorkParser(object):
    #Course info URL: https://w2prod.sis.yorku.ca/Apps/WebObjects/cdm.woa/wa/crsq?fa=LE&sj=ENG&cn=4000&cr=6.00&ay=2015&ss=FW
    base_url = "http://fides.ccs.yorku.ca/courseicals/"

    def __init__(self, logging):
        self._log = logging

    """ Returns a parsed BeautifulSoup object from given URL

    It will do GET and POST requests to the URL and send in a payload if supplied.
    """
    def soup_me(self, url, payload={}, type='GET'):
        if type == 'GET':
            req = requests.get(url, params=payload)
        elif type == 'POST':
            req = requests.post(url, params=payload)
        soup = BeautifulSoup(req.text.encode('utf-8'))
        return soup

    """ Return a full URL for a supplied url fragment

    This will combine a given url fragment to it's fully qualified version
    ie: /2015_LE_EECS ==> http://fides.ccs.yorku.ca/courseicals/2015_LE_EECS
    """
    def url_from_base(self, path):
        if path.startswith('/'):
            path = path[1:]
        return "%s%s" % (YorkParser.base_url, path)

    """ Get an array of all courses found inside the supplied folder name

    """
    def get_course_list(self, folder_name):
        self._log.info("Getting folder %s" % folder_name)
        subj_cal = self.soup_me(self.url_from_base(folder_name))
        regex = ("(?P<year>[0-9]{4})_(?P<faculty>[A-Z]{2})_(?P<department>[A-Z]+)_"
                "(?P<term>[A-Z]+)_(?P<code>[0-9]{4})__(?P<credits>[0-9]+)_"
                "(?P<section>[A-Z])_(?P<language>[A-Z]+)_A_(?P<type>[A-Z]+)_"
                "(?P<version>[0-9]{2})\.ics")
        return map(lambda x: self.course_dict(x.text, regex)
            , subj_cal.find_all('a', text=re.compile(regex)))

    """ Helper function to generate the course info from ics file name and the icse file itself
    """
    def course_dict(self, str, regex):
        g = re.search(regex, str)
        if g:
            course_info = {
                'year' : g.group('year'),
                'faculty': g.group('faculty'),
                'department': g.group('department'),
                'term': g.group('term'),
                'code': g.group('code'),
                'credits': g.group('credits'),
                'section': g.group('section'),
                'type': g.group('type'),
                'language': g.group('language'),
                'version': g.group('version'),
                'raw': str
            }
            #ICS file is requested here
            self._log.info("Getting ics %s" % str)
            course_ics = requests.get(self.url_from_base("%s_%s_%s/%s" %
                (course_info['year'], course_info['faculty'], course_info['department'], str)))
            cal = icalendar.Calendar.from_ical(course_ics.text)
            #Select the first "VEVENT" -- course schedule
            #some entries dont have this (tutorials, online courses, etc)
            events = cal.walk("VEVENT")
            if len(events) > 0:
                #Main event object containing the event data
                event = events[0]
                #More info handling this : https://github.com/collective/icalendar/tree/master/src/icalendar/tests
                # https://github.com/collective/icalendar
                # http://icalendar.readthedocs.org/en/latest/api.html
                # http://icalendar.readthedocs.org/en/latest/usage.html#more-documentation
                course_info = dict(course_info.items() + {
                    'calendar_data': event
                }.items())
            return course_info

        else:
            raise Exception("Cant get course info %s" % str)

    def get_subject_list(self, year):
        self._log.info("Getting %s" % year)
        course_cal = self.soup_me(self.base_url)
        regex = "%s_[A-Z]{2}_[A-Z]+/" % year
        return map(lambda x: x.text
            , course_cal.find_all('a', text=re.compile(regex)))


requests_cache.install_cache(expire_after=3600)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
parser = YorkParser(logging)

##SET THE YEAR HERE
subject_list = parser.get_subject_list(2014)

course_list = []

""" Testing code - uncomment to just run with one subject
course_list = parser.get_course_list(subject_list[0])
"""

#""" Production code - Runs the whole thing
for k in subject_list:
    course_list = course_list + parser.get_course_list(k)
#"""

pprint(course_list)

