import mechanize
import cookielib
from bs4 import BeautifulSoup
import json
import urllib
import csv
import datetime
import getpass

# This website uses a bunch of non-breaking spaces (&nbsp \xa0) to represent a blank
# this will replace them with a regular space also there seems to be some newlines
# getting thrown in there. This strips them.
def clean(text):
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
	if (len(tables) < 4):
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

		csvfile.writerow(
		[clean(header_spans[11].get_text()), # School Year
		clean(header_spans[7].get_text()), # Assessment Period
		clean(header_spans[13].get_text()), # School Name
		clean(header_spans[1].get_text()), # Teacher
		clean(header_spans[5].get_text()), # Class
		clean(header_spans[3].get_text()), # Assessment Date/Range
		clean(header_spans[9].get_text()), # Grade
		clean(header_spans[15].get_text()), # Report Date
		clean(divs[0].get_text()), #Student ID
		clean(divs[1].get_text()), #Student Name
		'{} {} {}'.format(clean(spans[8].get_text()), clean(spans[9].get_text()), clean(spans[10].get_text())), #DRA2 Level
		clean(divs[6].get_text()), #Percent of Accuracy
		clean(divs[7].get_text()), #Words Per Minute
		'{}/{}'.format(clean(spans[11].get_text()), clean(spans[13].get_text())), #Reading engagement
		'{}/{}'.format(clean(spans[14].get_text()), clean(spans[16].get_text())), #Oral Reading Fluency
		'{}/{}'.format(clean(spans[17].get_text()), clean(spans[19].get_text()))]) #Comprehension/PLC

	return

# Create a CSV file for output and write the header
# it's saved as a .txt file because otherwise google sheets or excel
# will interpret the student scores as dates. This forces you to use
# the data import wizard
filename = 'DRA Data {}.txt'.format(datetime.datetime.now())
print('Writing data to {}'.format(filename))
myfile = open(filename, 'w')
csvfile = csv.writer(myfile)
csvfile.writerow(['School Year', 'Assessment Period', 'School Name', 'Teacher', 'Class',
'Assessment Date/Range', 'Grade', 'Report Date', 'Student ID', 'Student Name', 'DRA2 Level',
'Percent of Accuracy', 'Words Per Minute', 'Reading Engagement', 'Oral Reading Fluency',
'Comprehension/PLC'])

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

# Now go to the report page

# The year is in the report page, I haven't found an AJAX call to get it so we
# have to use BeautifulSoup to parse the HTML
report_page = BeautifulSoup(br.open('https://dradashboard.com/DRA2Plus/reports/viewReport/17').read(), "html.parser")
for year in report_page.find(id='schoolYearId').find_all('option'):
	if year['value'] != "0":
		# From here on we can use AJAX calls to get the data we need
		print("Getting periods for year " + year.get_text())
		url = 'https://dradashboard.com/DRA2Plus/reports/loadFilterData/' + year['value'] + '/periodId'
		periods = json.loads(br.open(url).read())
		for period in periods['data']:
			print(" Getting schools for period " + period['value'])
			url = 'https://dradashboard.com/DRA2Plus/reports/loadFilterData/' + str(period['id']) + '/schoolId&' + year['value']
			schools = json.loads(br.open(url).read())
			for school in schools['data']:
				print("  Getting teachers for school " + school['value'])
				url = 'https://dradashboard.com/DRA2Plus/reports/loadFilterData/' + str(school['id']) + '/teacherId&' + year['value']
				teachers = json.loads(br.open(url).read())
				for teacher in teachers['data']:
					print("   Getting classes for teacher " + teacher['value'])
					url = 'https://dradashboard.com/DRA2Plus/reports/loadFilterData/' + str(teacher['id']) + '/classId&' + year['value'] + '&' + str(school['id'])
					classes = json.loads(br.open(url).read())
					for this_class in classes['data']:
						# We've got everything we need to manualy build a POST request
						print("    Getting report for class " + this_class['value'])
						parameters = {	'reportCategoryName' : 'Class',
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
						html = br.open('https://dradashboard.com/DRA2Plus/reports/generate', data).read()
						process_class_report(html, csvfile)
myfile.close()
