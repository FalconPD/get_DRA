"Webscrapes DRA data from Pearson DRA Dashboard Site"

import cookielib
import json
import getpass
import datetime
import csv
import urllib
import mechanize
from bs4 import BeautifulSoup

def clean(text):
    "Replaces non-breaking spaces and newlines with spaces and nothing respectively"

    return text.replace(u'\xa0', u' ').replace(u'\x0a', u'')

#def print_indexes(items):
#	i = 0
#	for item in items:
#		print('{}:{}'.format(i, clean(item.get_text())))
#		i += 1

def process_class_report(html, csvfile):
    "Takes a class report in HTML and converts it to CSV output"

    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all('table')

    # If we don't have at least 4 tables it's because there is no data
    # for this teacher
    if len(tables) < 4:
        return

    # The header is the 3rd table and the student data is the 4th
    header = tables[2]
    data = tables[3]

    # The spans in the header tell us Teacher Name, Asessment Date/Range, Class, Assessment Period
    # Grade, School Year, School Name, and Report Date
    header_spans = header.find_all('span')

    # We only want the direct children for the data table since each row has another table in it
    # The first four data rows are column headers and nonsense
    for row in data.find_all('tr', recursive=False)[4:]:
        # The first two divs are StudentID and StudentName and some score data
        divs = row.find_all('div')

        # The spans contain the actual scores in a funky format
        spans = row.find_all('span')

        #print('Divs')
        #print(divs)
        #print_indexes(divs)
        #print('Spans')
        #print(spans)
        #print_indexes(spans)

        csvfile.writerow([
            clean(header_spans[11].get_text()), # School Year
            clean(header_spans[7].get_text()), # Assessment Period
            clean(header_spans[13].get_text()), # School Name
            clean(header_spans[1].get_text()), # Teacher
            clean(header_spans[5].get_text()), # Class
            clean(header_spans[3].get_text()), # Assessment Date/Range
            clean(header_spans[9].get_text()), # Grade
            clean(header_spans[15].get_text()), # Report Date
            clean(divs[0].get_text()), # Student ID
            clean(divs[1].get_text()), # Student Name
            '{} {} {}'.format( # DRA2 Level
                clean(spans[8].get_text()),
                clean(spans[9].get_text()),
                clean(spans[10].get_text())),
            clean(divs[6].get_text()), #Percent of Accuracy
            clean(divs[7].get_text()), #Words Per Minute
            '{}/{}'.format( # Reading engagement
                clean(spans[11].get_text()),
                clean(spans[13].get_text())),
            '{}/{}'.format( # Oral Reading Fluency
                clean(spans[14].get_text()),
                clean(spans[16].get_text())),
            '{}/{}'.format( # Comprehension/PLC
                clean(spans[17].get_text()),
                clean(spans[19].get_text()))])

    return

def main():
    "Main function"

    # Browser
    br = mechanize.Browser()

    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browswer options
    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    br.addheaders = [('User-agent', 'Chrome')]

    # Start by logging in to Pearson
    br.open('https://dradashboard.com/DRA2Plus/login')

    br.select_form(nr=0)

    br.form['username'] = raw_input("Username: ")
    br.form['password'] = getpass.getpass("Password: ")

    br.submit()

    # Create a CSV file for output and write the header
    filename = 'DRA Data {}.txt'.format(datetime.datetime.now())
    print 'Writing data to {}'.format(filename)
    myfile = open(filename, 'w')
    csvfile = csv.writer(myfile)
    csvfile.writerow([
        'School Year',
        'Assessment Period',
        'School Name',
        'Teacher',
        'Class',
        'Assessment Date/Range',
        'Grade',
        'Report Date',
        'Student ID',
        'Student Name',
        'DRA2 Level',
        'Percent of Accuracy',
        'Words Per Minute',
        'Reading Engagement',
        'Oral Reading Fluency',
        'Comprehension/PLC'])

    # Now go to the report page

    # The years are in the report page, I haven't found an AJAX call to get it so we
    # have to use BeautifulSoup to parse the HTML. The first year has no value
    url = 'https://dradashboard.com/DRA2Plus/reports/viewReport/17'
    report_page = BeautifulSoup(br.open(url).read(), 'html.parser')
    for year in report_page.find(id='schoolYearId').find_all('option')[1:]:
        # From here on we can use AJAX calls to get the data we need
        print 'Getting periods for year {}'.format(year.get_text())
        url = 'https://dradashboard.com/DRA2Plus/reports/loadFilterData/{}/periodId'.format(
            year['value'])
        periods = json.loads(br.open(url).read())
        for period in periods['data']:
            print ' Getting schools for period {}'.format(period['value'])
            url = 'https://dradashboard.com/DRA2Plus/reports/loadFilterData/{}/schoolId&{}'.format(
                str(period['id']), year['value'])
            schools = json.loads(br.open(url).read())
            for school in schools['data']:
                print '  Getting teachers for school {}'.format(school['value'])
                url = ('https://dradashboard.com/DRA2Plus/reports/loadFilterData/{}/'
                       'teacherId&{}').format(str(school['id']), year['value'])
                teachers = json.loads(br.open(url).read())
                for teacher in teachers['data']:
                    print '   Getting classes for teacher {}'.format(teacher['value'])
                    url = ('https://dradashboard.com/DRA2Plus/reports/loadFilterData/{}/'
                           'classId&{}&{}').format(str(teacher['id']), year['value'],
                                                   str(school['id']))
                    classes = json.loads(br.open(url).read())
                    for this_class in classes['data']:
                        # We've got everything we need to manualy build a POST request
                        print '    Getting report for class {}'.format(this_class['value'])
                        parameters = {
                            'reportCategoryName' : 'Class',
                            'skillName' : '0',
                            'myid' : 'true',
                            'schoolYearId' : year['value'],
                            'draTypeId' : '1',
                            'periodId' : period['id'],
                            'schoolId' : school['id'],
                            'teacherId' : teacher['id'],
                            'classId' : this_class['id'],
                            'viewType' : 'html',
                            'reportName' : 'Class Reporting Form'}
                        data = urllib.urlencode(parameters)
                        url = 'https://dradashboard.com/DRA2Plus/reports/generate'
                        html = br.open(url, data).read()
                        process_class_report(html, csvfile)
    myfile.close()
    exit(0)

if __name__ == "__main__":
    main()
