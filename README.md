# get_DRA
Python script to pull down DRA data

This script connects to [Pearson DRA Dashboard](http://dradashboard.com) and
uses the login credentials you are prompted for to obtain a session cookie.
It then pulls down and parses the class reporting form page and uses the year
data to look up all the other data necessary to generate a report. Normally this
is done automatically through AJAX calls as the dropdown menus are clicked. This
script goes through every permutation and generates a report for each. The
reports are processed using [Beautifulsoup](http://www.crummy.com/software/BeautifulSoup/)
to grab the relevant data which is saved to an excel file using
[openpyxl](https://openpyxl.readthedocs.org/en/2.5/). More info can be found in
the source code comments.
