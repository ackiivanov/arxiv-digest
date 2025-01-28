#!/usr/bin/python3
#encoding=utf8

version = "A4.3"
# Created by suuuehgi (https://github.com/suuuehgi)
# Modified by Aleksandar Ivanov (https://github.com/ackiivanov)

import os, re, sys, subprocess, shutil

import configparser

from datetime import date

import urllib.request as urllib
from bs4 import BeautifulSoup

import smtplib
from email.mime.text import MIMEText

# Beatiful Soup throws a false warning when a website uses XHTML.
# We ignore this warning
import warnings
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)


# ================================== Settings ===================================
# These are hardcoded settings that the script uses to find relevant files,
# get the email account information and set the style of saved files.

# The home directory is where the script is saved. The download directory is
# where the digest and downloaded papers are saved. Configurations will be
# saved in HOME_PATH/.config/arxiv.conf.
HOME_PATH = os.path.expanduser('~/Scripts/arxiv-digest')
DOWNLOAD_PATH = os.path.expanduser('~/Papers/arxiv-digest/{}'.format(date.today()))

# To also receive an email with the digest, a non-empty email address needs to be set.
# An empty string will not send an email. The script will try to only send one email
# a day even if it is run multiple times. For Gmail addresses an 'app password' can
# be used for successful login if 2FA is enabled.
EMAIL = ''
EMAIL_LOGIN = ''

# The possible attributes that a given paper can have for use in the filename style.
# The style is overwritten by the config file if it has such a configuration set.
ATTRIBUTES = ['arxivid', 'url', 'categories', 'title', 'abstract', 'authors', 'comments']
STYLE_STD = "($arxivid) $title - $authors.pdf"

# ===============================================================================


# To add colors and weight to terminal output. They act like parentheses and always
# have to be closed with END.
class Color:

  def __init__(self, is_colored):

    if is_colored:
      self.BLACK = '\033[90m'
      self.RED = '\033[91m'
      self.GREEN = '\033[92m'
      self.YELLOW = '\033[93m'
      self.BLUE = '\033[94m'
      self.PURPLE = '\033[95m'
      self.CYAN = '\033[96m'
      self.WHITE = '\033[97m'
    else:
      self.BLACK = ''
      self.RED = ''
      self.GREEN = ''
      self.YELLOW = ''
      self.BLUE = ''
      self.PURPLE = ''
      self.CYAN = ''
      self.WHITE = ''
  
    self.BOLD = '\033[1m'
    self.ITALIC = '\033[3m'
    self.UNDERLINE = '\033[4m'
    self.END = '\033[0m'

# Set of global variables that keep track of how many papers have been filtered
class Statistics:
  replaced = 0
  cat_blacklist = 0
  duplicate = 0
  key_blacklist = 0


def config_write(config_dict, home=HOME_PATH):
  
  config = configparser.ConfigParser()

  if not os.path.exists(home + '/.config'):
    print('Creating .config folder')
    os.mkdir(home + '/.config')

  config['SETTINGS'] = config_dict

  with open(home + '/.config/arxiv.conf', 'w') as configfile:
    config.write(configfile)

def config_read(home=HOME_PATH):

  config = configparser.ConfigParser()

  if os.path.exists(home + '/.config/arxiv.conf'):
    config.read(home + '/.config/arxiv.conf')
    return config['SETTINGS']

  else:
    return None

# Function that gets the list of categories from the arxiv front page. It curently works in a
# somewhat ad-hoc way that depends on the way arxiv.org is laid out in html. It may break in the future. Currently displays too many categories... (to fix?)
def get_cat_list():
  
  request = urllib.Request("https://arxiv.org/", headers={'User-Agent': 'Mozilla/5.0'})
  home_page_html = urllib.urlopen(request)
  soup = BeautifulSoup(home_page_html, features="lxml")

  pages = soup.find_all("a", href=re.compile("/list/"))

  category_prev = ""
  cats = {}
  n = 0
  for page in pages:

    category = page.parent.parent.previous_sibling.previous_sibling.get_text()

    # Print category once
    if category != category_prev:
      print('\n' + color.BOLD + '~ ~ ~ {}'.format(category.upper()) + color.END)
      category_prev = category

    # Search for previous words written in bold
    if page.previous_sibling.previous_sibling.name == 'b':
      tag = page.previous_sibling.previous_sibling.previous_sibling.previous_sibling.get_text()

      # For small categories, don't write them twice
      if tag != category_prev:
        print('\n' + page.previous_sibling.previous_sibling.previous_sibling.previous_sibling.get_text())

    print('{:4}: '.format(n) + page.get_text())
    cats[n] = page.get('href')[6:-7]
    n += 1

  return cats

def setup(std_style=STYLE_STD):

  config = {}

  while True:

    print('The default style for filenames of downloaded files is "{}". '.format(std_style))
    style_choice = input('If you wish to change this enter your preferred style in the same ' +
                          'format. Beware that the length of filenames is limited by your ' +
                          'filesystem. Available keywords are: {}: '.format(ATTRIBUTES))

    if style_choice == '':
      print('The default style will be used. This can be changed in ' +
             '{}/.config/arxiv.conf.'.format(HOME_PATH))
      config['STYLE'] = std_style
      break

    elif not set(re.findall(r'[A-Za-z]+', style_choice)).issubset(ATTRIBUTES):
      print('{} is not a valid style choice. Try again.'.format(style_choice))
      continue
    
    print('Your style will be set to: {}'.format(style_choice))
    config['STYLE'] = style_choice
    break

  while True:
    
    color_choice = input('Do you wish for terminal output to be colored? (y/n)')
    color_choice = color_choice.lower()

    if color_choice == 'y' or color_choice == 'n':
      config['COLORED'] = color_choice
    
    else:
      print('{} is not a valid choice. Try again.'.format(color_choice))


  categories = get_cat_list()
  while True:

    choices = input('\n' + 'Enter a space-separated list of the categories you want to subscribe ' +
                     'to. You can then optionally add a ; and another space-separated list of ' +
                     'the categories you would like to blacklist.' + color.BOLD +
                     '(e.g. 2 12 5 ; 1 20)' + color.END + ': ')

    if choices == '':
      print('You will not be subscribed to any categories. This can be changed in ' +
             '{}/.config/arxiv.conf.'.format(HOME_PATH))
      config['CATEGORY_WHITELIST'] = ''
      config['CATEGORY_BLACKLIST'] = ''
      config['KEYWORD_BLACKLIST'] = ''

      config_write(config)
      return 0

    try:
      choices = choices.split(';')
      if len(choices) == 1:
        whitelist = [categories[int(i)] for i in choices[0].split() if int(i) <= n]
        blacklist = ''
      elif len(choices) == 2:
        whitelist = [categories[int(i)] for i in choices[0].split() if int(i) <= n]
        blacklist = [categories[int(i)] for i in choices[1].split() if int(i) <= n]
      else:
        raise ValueError

    except ValueError:
      print('{} is not a valid selection. Try again.'.format(choices))
      continue
    
    print("You will be subscribed to the following categories: {}".format(whitelist))
    config['CATEGORY_WHITELIST'] = '; '.join(whitelist)
    
    if blacklist != []:
      print("The following categories will be blacklisted: {}".format(blacklist))
    config['CATEGORY_BLACKLIST'] = '; '.join(blacklist)
    break

  while True:
    
    choices = input('\n' + 'Additionally, you can choose keywords that you wish to be ' +
                     'blacklisted. If you want to make use of this option, enter the ' +
                     'keywords as a colon-separated list of lowercase-only characters.' +
                     color.BOLD + '(e.g. heisenberg; gravitational waves; f(r,t)...)' +
                     color.END + ': ')
  
    if choices == "":
      print('No keywords will be blacklisted. This can be changed in ' +
           '{}/.config/arxiv.conf.'.format(HOME_PATH))
      config['KEYWORD_BLACKLIST'] = ""
      break
  
    elif choices.lower() != choices:
      print('The input is not fully in lowercase characters. Try again.')
      continue
  
    print('The following keywords will be blacklisted: {}'.format(choices.split('; ')))
    config['KEYWORD_BLACKLIST'] = choices
    break

  config_write(config)
  print('The configuration has be set up.')
  
  return 0


def on_blacklist(replaced, arxivid, categories, title, abstract, cat_blacklist, key_blacklist, papers):
  
  if replaced:
    Statistics.replaced += 1
    return True

  for catb in cat_blacklist:
    if catb in categories:
      Statistics.cat_blacklist += 1
      return True

  for recorded_paper in papers:
    if recorded_paper['arxivid'] == arxivid:
      Statistics.duplicate += 1
      return True

  for keyword in key_blacklist:
    if (keyword in title.lower()) or (keyword in abstract.lower()):
      Statistics.key_blacklist += 1
      return True
    
  return False

# Generator that runs over a category and yields the data of a paper as a dictionary
# if the paper is not blacklisted. This is also somewhat ad-hoc as above.
def paper_data_scraper(category, cat_blacklist, key_blacklist, papers):

  cat_url = 'https://arxiv.org/list/' + category + '/new'
  
  try:
    request = urllib.Request(cat_url, headers={'User-Agent': 'Mozilla/5.0'})
    cat_html = urllib.urlopen(request)
  except urllib.HTTPError:
    raise urllib.HTTPError("'{}' not found.".format(cat_url))
    sys.exit(0)

  # Scrape the webpage for all its text
  soup = BeautifulSoup(cat_html, features="lxml")

  # Get paper head data and metadata
  papers_head = soup.find_all("dt")
  papers_meta = soup.find_all("div", class_="meta")
  try:
    zipped_papers_data = zip(papers_head, papers_meta, strict=True)
  except ValueError:
    raise ValueError("ERROR: The number of found papers does not match the number of titles. It is very likely that this script does not work anymore.")
    
  for paper_head, paper_meta in zipped_papers_data:

    arxivid = paper_head.find_all("a", title="Abstract")[0].get_text().replace('arXiv:', '').strip()
    url = 'https://arxiv.org/pdf/' + arxivid

    replaced = ('(replaced)' in paper_head.get_text())
    
    categories = paper_meta.find("div", class_="list-subjects")
    categories = categories.get_text().replace('Subjects:\n', '').strip()

    title = paper_meta.find("div", class_="list-title")
    title = title.get_text().replace('Title:\n', '').strip()

    try:
      abstract = paper_meta.find("p", class_="mathjax").get_text().replace('\n',' ').strip()
    except AttributeError:
      abstract = "/"
    
    # Check if the paper is on the blacklist before the data collection finishes
    # for a slight efficiency boost
    if on_blacklist(replaced, arxivid, categories, title, abstract, cat_blacklist, key_blacklist, papers):
      continue
    
    # Fetch authors from the links with their names
    authors = paper_meta.find("div", class_="list-authors")
    authors = [a.get_text().strip() for a in authors.find_all('a')]
    authors = ', '.join(authors)
        
    try:
      comments = paper_meta.find("div", class_="list-comments").get_text()
      comments = comments.replace('Comments:\n', '').strip()
    except AttributeError:
      comments = "/"    
    
    yield {'arxivid': arxivid, 'categories': categories, 'title': title, 'replaced': replaced,
            'abstract': abstract, 'authors': authors, 'comments': comments, 'url': url}

def list_papers(cat_whitelist, cat_blacklist, key_blacklist):

  papers = []
  total_papers = 0

  for cat in cat_whitelist:
    for paper in paper_data_scraper(cat, cat_blacklist, key_blacklist, papers):
        papers.append(paper)

  return papers, total_papers


def download_prompt(number_of_papers):

  if number_of_papers == 0:
    return []
  
  download_list = []
  while True:

    download_list = input('\n' + color.BOLD + color.UNDERLINE + color.BLACK + 'Which papers would you like to download (e.g. 0 3 14 ...):' + color.END + ' ')

    if download_list == "":
      print(color.BLACK + 'Nothing will be downloaded.' + color.END)
      break

    try:
      download_list = [int(i) for i in download_list.split()]
      if (min(download_list) < 0) or (max(download_list) > number_of_papers): raise ValueError
    except ValueError:
      print('{} is not a valid list of papers to download. Try again.'.format(download_list))
      continue

    break

  return download_list

def downloader(download_list, papers, style):

  if len(download_list) == 0:
    return 0
  
  try:
    os.mkdir(DOWNLOAD_PATH + '/Papers')
  except FileExistsError:
    pass

  # Get maximum filename length supported by OS to avoid errors with filenames
  # that are too long to be displayed
  NAME_MAX = subprocess.check_output("getconf NAME_MAX /", shell=True).strip()
  NAME_MAX = int(NAME_MAX)

  for paper_index in download_list:

    # Construct filename according to style
    filename = style
    for style_option in ATTRIBUTES:
      filename = filename.replace('$' + style_option, papers[paper_index][style_option])
    
    if len(filename) > NAME_MAX:
      print('WARNING: Your file system supports file names up to {} characters'.format(NAME_MAX) +
             ', but your chosen style gives a name longer than that. Hence the arXiv id number ' +
             'will be used to name the file: {}.pdf'.format(papers[paper_index]["arxivid"]))
      filename = papers[paper_index]["arxivid"] + ".pdf"

    # Download the file using wget
    subprocess.call(['wget', '--quiet', '--show-progress', '--header',
                     'User-Agent: Mozilla/5.0', '--output-document',
                     DOWNLOAD_PATH + '/Papers/' + filename, papers[paper_index]["url"]])
  
  return 0


def draw_bar(number_passed, bar_length=120):

  # if the bar length is too big it won't fit well in the terminal
  terminal_width = shutil.get_terminal_size().columns
  if bar_length + 10 > terminal_width:
    bar_length = terminal_width - 10

  total_number = (Statistics.replaced + Statistics.cat_blacklist + Statistics.duplicate
                   + Statistics.key_blacklist + number_passed)

  rounded_replaced = max(round(bar_length * Statistics.replaced / total_number), 1)
  rounded_cat_blacklist = max(round(bar_length * Statistics.cat_blacklist / total_number), 1)
  rounded_duplicate = max(round(bar_length * Statistics.duplicate / total_number), 1)
  rounded_key_blacklist = max(round(bar_length * Statistics.key_blacklist / total_number), 1)
  rounded_passed = bar_length - rounded_replaced - rounded_cat_blacklist - rounded_duplicate - rounded_key_blacklist

  bar = (color.BLUE + '[' +'=' * (rounded_passed - 1) + '|' + color.END +
         color.YELLOW + '=' * (rounded_duplicate - 1) + '|' + color.END + 
         color.PURPLE + '=' * (rounded_cat_blacklist - 1) + '|' + color.END +
         color.RED + '=' * (rounded_key_blacklist - 1) + '|' + color.END +
         color.BLACK + '=' * rounded_replaced + ']' + color.END)
  number = (' {}/{}'.format(total_number - number_passed, total_number))

  print('\n' + color.WHITE + 'Filter Statistics:                 ' + color.END +
         color.BLUE + '(Shown Papers) ' + color.END +
         color.YELLOW + '(Duplicates) ' + color.END +
         color.PURPLE + '(Blacklisted Category) ' + color.END +
         color.RED + '(Blacklisted Keywords) ' + color.END +
         color.BLACK + '(Replaced Papers)' + color.END)
  print(' ' * ((terminal_width - bar_length - 2) // 2) + bar + color.WHITE + number + color.END)

# ANSI colors do slow things down a bit
def print_to_terminal(papers):
  
  for i, paper in enumerate(papers):

    print('\n')
    print(color.BOLD + color.UNDERLINE + color.BLUE + '{:5}'.format(i) + color.END + ' ' + color.ITALIC + color.WHITE
           + paper["title"] + color.END + color.RED + ' (' + paper["arxivid"] + ')' + color.END)
    print(6 * ' ' + color.BLACK + 'Authors: ' + paper["authors"] + color.END)
    print(6 * ' ' + color.BLACK + 'Subjects: ' + paper["categories"] + color.END)
    print(6 * ' ' + color.BLACK + 'Comments: ' + paper["comments"] + color.END + '\n')        
    print(color.BLUE + paper["abstract"] + color.END + '\n')
    print(color.GREEN + '-' * 167 + color.END)

  draw_bar(len(papers))

def print_to_file(papers):
  
  try:
    os.remove(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()))
  except FileNotFoundError:
    pass

  with open(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()), 'a+') as output:
    output.write("This is the daily arXiv digest for the date {}. ".format(date.today())
                 + "The categories that have been accessed were: {}. ".format(cat_whitelist)
                 + "The ones that were blacklisted were: {}. ".format(cat_blacklist)
                 + "The blacklisted keywords were: {}".format(key_blacklist)
                 + "This can be changed in the file {}/.config/arxiv.conf.\n\n".format(HOME_PATH))
  
  for i, paper in enumerate(papers):

    with open(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()), 'a+') as output:
      output.write('\n\n' + '{:5}:'.format(i) + paper["title"]
                    + ' (' + paper["arxivid"] + ')' + '\n')
      output.write(6 * ' ' + 'Authors: ' + paper["authors"] + '\n')
      output.write(6 * ' ' + 'Subjects:' + paper["categories"] + '\n')
      output.write(6 * ' ' + 'Comments:' + paper["comments"] + '\n\n')
      output.write(paper["abstract"] + '\n\n')
      output.write('---------------------------------------------------------------------')

def send_email(from_email=EMAIL, from_password=EMAIL_LOGIN, to_email=EMAIL):

  if from_email is None:
    return 0

  try:
    with open(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()), 'r') as output:
      message = output.read()
  except IOError:
    print(color.YELLOW + 'WARNING: Email will not be sent because message is empty.' + color.END)
    return 0
  
  email_data = MIMEText(message)
  email_data['Subject'] = "arXiv Digest {}".format(date.today())
  email_data['From'] = from_email
  email_data['To'] = to_email

  server = smtplib.SMTP('smtp.gmail.com', 587)
  server.ehlo()
  server.starttls()
  server.login(from_email, from_password)
  server.sendmail(from_email, to_email, msg.as_string())
  server.close()

  return 0


if __name__ == "__main__":

  # ============================== Argument Parser ==============================

  if any([1 if arg in sys.argv else 0 for arg in ['-v', '--version']]):
    print(version)
    sys.exit(0)

  if any([1 if arg in sys.argv else 0 for arg in ['-h', '--help']]):
    name = os.path.basename(sys.argv[0])

    print("This is {}. Get your daily arXiv dose.".format(name))
    print("Usage: run command `python3 {}.py'.".format(name))
    print("The python package `beatiful soup' is a requirement. Additionally, the package" +
           "`wget' is also a requirement if downloading papers.")
    print("'-h, --help': print help")
    print("'-v, --version': print version")
    print("'--config': Set up basic configuration in {}/.config/arxiv/conf".format(HOME_PATH))

    sys.exit(0)

  if any([1 if arg in sys.argv else 0 for arg in ['--config']]):
    setup()
    sys.exit(0)

  # =============================================================================


  # =============================== Configuration ================================

  config = config_read()
  if not config:
    print('No configuration file found, generating one now...')
    setup()
    config = config_read()  

  style = config['STYLE']
  color = Color(config['COLORED'] == 'y')
  cat_whitelist = [s.strip() for s in config['CATEGORY_WHITELIST'].split(';') if s != ""]
  cat_blacklist = [s.strip() for s in config['CATEGORY_BLACKLIST'].split(';') if s != ""]
  key_blacklist = [s.strip() for s in config['KEYWORD_BLACKLIST'].split(';') if s != ""]

  # =============================================================================


  # =============================== Fetch Papers ================================

  papers, total_papers = list_papers(cat_whitelist, cat_blacklist, key_blacklist)

  # =============================================================================


  # =============================== Print Output ================================

  # Create the day's directory. If the directory exists don't send an email to
  # limit the number of emails to one per day
  try:
    os.mkdir(DOWNLOAD_PATH)
    from_address = EMAIL
  except FileExistsError:
    from_address = None

  print_to_terminal(papers)

  print_to_file(papers)

  send_email(from_email=from_address)

  # =============================================================================


  # ============================= Download Papers ======================+========

  download_list = download_prompt(len(papers))

  downloader(download_list, papers, style)

  # =============================================================================


