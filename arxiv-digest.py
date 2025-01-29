#!/usr/bin/python3
#encoding=utf8

version = 'A5.1'
# Created by suuuehgi (https://github.com/suuuehgi)
# Modified by Aleksandar Ivanov (https://github.com/ackiivanov)

import os, re, sys, subprocess, shutil

import configparser

from datetime import date
import time

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
STYLE_STD = '($arxivid) $title - $authors.pdf'

# ===============================================================================


# To add colors and weight to terminal output. They act like parentheses and always
# have to be closed with END. ANSI colors do slow the loading of the terminal to some degree
class Color:

  def __init__(self, colored_output):

    if colored_output:
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

  try:
    config.read(home + '/.config/arxiv.conf')
    return config['SETTINGS']
  except:
    raise FileNotFoundError


# Function that gets the list of categories from the arxiv front page. It curently works
# in a somewhat ad-hoc way that depends on the way arxiv.org is laid out in html.
# It may break in the future.
def cat_list_prompt(color):
  
  request = urllib.Request('https://arxiv.org/', headers={'User-Agent': 'Mozilla/5.0'})
  home_page_html = urllib.urlopen(request)
  soup = BeautifulSoup(home_page_html, features='lxml')

  home_page_links = soup.find_all('a', href=re.compile('/list/'))

  subject_prev = ''
  categories = {}
  n = 0
  for link in home_page_links:

    # Print the overaching subject name the first time it appears
    subject_name = link.parent.parent.previous_sibling.previous_sibling.get_text()
    if subject_name != subject_prev:
      print('\n' + color.BOLD + color.UNDERLINE + '~ ~ ~ {} ~ ~ ~'.format(subject_name.upper()) + color.END)
      subject_prev = subject_name

    # If the subject has subsubjects they appear close to the link for the new papers in that subsubject. The href of the link looks like /list/---?---/new so this is where we extract the id from, but the subsubject name has to be extracted from nearby and not the link itself. Beware that the subsubject name may not be the same as the subject name even if there is only one subsubject, as is the case of Computer Science, where additionally the link of the named subsubject leads to a help page instead.
    link_name = link.get_text()
    if 'new' in link_name:
      subsubject_name = link.previous_sibling.previous_sibling.previous_sibling.previous_sibling.get_text()
      subsubject_id = link.get('href')[6:-4]
      print('  {:4}: '.format(n) + color.UNDERLINE + subsubject_name + color.END + ' ({})'.format(subsubject_id) + ':')
      categories[n] = subsubject_id
      n += 1
    
    # The href of the link looks like '/list/---?---/recent' so that is how we extract the id
    if link_name != 'new' and link_name != 'recent':
      link_id = link.get('href')[6:-7]
      print('    {:4}: '.format(n) + link_name + ' ({})'.format(link_id))
      categories[n] = link_id
      n += 1    

  return categories

def setup(color, std_style=STYLE_STD):

  config = {}

  while True:

    print()
    style_choice = input("The default style for filenames of downloaded files is `{}'.\n".format(std_style)
                         + 'You can change it by entering a style of the same format using the keywords\n'
                         + '(' + ', '.join(ATTRIBUTES) + '): ')

    if style_choice == '':
      print('[info] The default style will be used. This can be changed in ' +
             '{}/.config/arxiv.conf.\n'.format(HOME_PATH))
      config['STYLE'] = std_style
      break

    elif not {x[1:] for x in re.findall(r'\$[a-z]+', style_choice)}.issubset(ATTRIBUTES):
      print('{} is not a valid style choice. Try again.'.format(style_choice))
      continue
    
    print('[info] Your style will be set to: {}\n'.format(style_choice))
    config['STYLE'] = style_choice
    break

  while True:
    
    color_choice = input('Do you wish for terminal output to be colored? (Y/n)')
    color_choice = color_choice.lower()

    if color_choice == 'y' or color_choice == '':
      print('[info] Terminal output will be colored.')
      config['COLORED'] = 'y'
      break
    
    elif color_choice == 'n':
      print('[info] Terminal output will not be colored.')
      config['COLORED'] = 'n'
      break
    
    else:
      print('{} is not a valid choice. Try again.'.format(color_choice))


  categories = cat_list_prompt(color)
  while True:

    choices = input('Enter a space-separated list of the categories you want to subscribe ' +
                    'to.\nYou can then optionally add a ; and another space-separated list of ' +
                    'categories\nyou would like to blacklist. ' + color.BOLD +
                    '(e.g. 2 12 5 ; 1 20)' + color.END + ': ')

    if choices == '':
      print('[info] You will not be subscribed to any categories. This can be changed in ' +
             '{}/.config/arxiv.conf.\n'.format(HOME_PATH))
      config['CATEGORY_WHITELIST'] = ''
      config['CATEGORY_BLACKLIST'] = ''
      config['KEYWORD_BLACKLIST'] = ''

      config_write(config)
      return 0

    try:
      choices = choices.split(';')
      if len(choices) == 1:
        whitelist = [categories[int(i)] for i in choices[0].split() if int(i) <= len(categories)]
        blacklist = ''
      elif len(choices) == 2:
        whitelist = [categories[int(i)] for i in choices[0].split() if int(i) <= len(categories)]
        blacklist = [categories[int(i)] for i in choices[1].split() if int(i) <= len(categories)]
      else:
        raise ValueError

    except ValueError:
      print('{} is not a valid selection. Try again.'.format(choices))
      continue
    
    print('[info] You will be subscribed to the following categories:\n' +
          ', '.join(whitelist) + '\n')
    config['CATEGORY_WHITELIST'] = '; '.join(whitelist)
    
    if blacklist != []:
      print('[info] The following categories will be blacklisted:\n' + 
            ', '.join(blacklist) + '\n')
    config['CATEGORY_BLACKLIST'] = '; '.join(blacklist)
    
    break

  while True:
    
    choices = input('Additionally, you can choose keywords that you wish to be ' +
                    'blacklisted.\nIf you want to make use of this option, enter the ' +
                    'keywords as a colon-separated\nlist of lowercase-only characters.' +
                    color.BOLD + '(e.g. einstein equation; f(r,t); ...)' +
                    color.END + ': ')
  
    if choices == '':
      print('[info] No keywords will be blacklisted. This can be changed in ' +
           '{}/.config/arxiv.conf.\n'.format(HOME_PATH))
      config['KEYWORD_BLACKLIST'] = ''
      break
  
    elif choices.lower() != choices:
      print('The input is not fully in lowercase characters. Try again.')
      continue
  
    print('[info] The following keywords will be blacklisted:\n' +
          ', '.join(choices.split('; ')) + '\n')
    config['KEYWORD_BLACKLIST'] = choices
    break

  config_write(config)
  print('[info] The configuration has be set up.')
  time.sleep(1)
  
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
  soup = BeautifulSoup(cat_html, features='lxml')

  # Get paper head data and metadata
  papers_head = soup.find_all('dt')
  papers_meta = soup.find_all('div', class_='meta')
  try:
    zipped_papers_data = zip(papers_head, papers_meta, strict=True)
  except ValueError:
    raise ValueError('ERROR: The number of found papers does not match the number of titles. It is very likely that this script does not work anymore.')
    
  for paper_head, paper_meta in zipped_papers_data:

    arxivid = paper_head.find_all('a', title='Abstract')[0].get_text().replace('arXiv:', '').strip()
    url = 'https://arxiv.org/pdf/' + arxivid

    replaced = ('(replaced)' in paper_head.get_text())
    
    categories = paper_meta.find('div', class_='list-subjects')
    categories = categories.get_text().replace('Subjects:\n', '').strip()

    title = paper_meta.find('div', class_='list-title')
    title = title.get_text().replace('Title:\n', '').strip()

    try:
      abstract = paper_meta.find('p', class_='mathjax').get_text().replace('\n',' ').strip()
    except AttributeError:
      abstract = '/'
    
    # Check if the paper is on the blacklist before the data collection finishes
    # for a slight efficiency boost
    if on_blacklist(replaced, arxivid, categories, title, abstract, cat_blacklist, key_blacklist, papers):
      continue
    
    # Fetch authors from the links with their names
    authors = paper_meta.find('div', class_='list-authors')
    authors = [a.get_text().strip() for a in authors.find_all('a')]
    authors = ', '.join(authors)
        
    try:
      comments = paper_meta.find('div', class_='list-comments').get_text()
      comments = comments.replace('Comments:\n', '').strip()
    except AttributeError:
      comments = '/'    
    
    yield {'arxivid': arxivid, 'categories': categories, 'title': title, 'replaced': replaced,
            'abstract': abstract, 'authors': authors, 'comments': comments, 'url': url}

def list_papers(cat_whitelist, cat_blacklist, key_blacklist):

  papers = []
  total_papers = 0

  for cat in cat_whitelist:
    for paper in paper_data_scraper(cat, cat_blacklist, key_blacklist, papers):
        papers.append(paper)

  return papers, total_papers


def download_prompt(number_of_papers, color):

  if number_of_papers == 0:
    return []
  
  download_list = []
  while True:

    download_list = input('\n' + color.BOLD + color.UNDERLINE + color.BLACK + 'Which papers would you like to download (e.g. 0 3 14 ...):' + color.END + ' ')

    if download_list == '':
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
  NAME_MAX = subprocess.check_output('getconf NAME_MAX /', shell=True).strip()
  NAME_MAX = int(NAME_MAX)

  for paper_index in download_list:

    # Construct filename according to style
    filename = style
    for style_option in ATTRIBUTES:
      filename = filename.replace('$' + style_option, papers[paper_index][style_option])
    
    if len(filename) > NAME_MAX:
      print('WARNING: Your file system supports file names up to {} characters'.format(NAME_MAX) +
             ', but your chosen style gives a name longer than that. Hence the arXiv id number ' +
             'will be used to name the file: {}.pdf'.format(papers[paper_index]['arxivid']))
      filename = papers[paper_index]['arxivid'] + '.pdf'

    # Download the file using wget
    subprocess.call(['wget', '--quiet', '--show-progress', '--header',
                     'User-Agent: Mozilla/5.0', '--output-document',
                     DOWNLOAD_PATH + '/Papers/' + filename, papers[paper_index]['url']])
  
  return 0


def draw_bar(number_passed, color, bar_length=120):

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

def print_to_terminal(papers, color):
  
  for i, paper in enumerate(papers):

    print('\n')
    print(color.BOLD + color.UNDERLINE + color.BLUE + '{:5}'.format(i) + color.END + ' ' + color.ITALIC + color.WHITE
           + paper['title'] + color.END + color.RED + ' (' + paper['arxivid'] + ')' + color.END)
    print(6 * ' ' + color.BLACK + 'Authors: ' + paper['authors'] + color.END)
    print(6 * ' ' + color.BLACK + 'Subjects: ' + paper['categories'] + color.END)
    print(6 * ' ' + color.BLACK + 'Comments: ' + paper['comments'] + color.END + '\n')        
    print(color.BLUE + paper['abstract'] + color.END + '\n')
    print(color.GREEN + '-' * 167 + color.END)

  draw_bar(len(papers), color)

def print_to_file(papers):
  
  try:
    os.remove(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()))
  except FileNotFoundError:
    pass

  with open(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()), 'a+') as output:
    output.write('This is the daily arXiv digest for the date {}. '.format(date.today())
                 + 'The categories that have been accessed were: {}. '.format(cat_whitelist)
                 + 'The ones that were blacklisted were: {}. '.format(cat_blacklist)
                 + 'The blacklisted keywords were: {}'.format(key_blacklist)
                 + 'This can be changed in the file {}/.config/arxiv.conf.\n\n'.format(HOME_PATH))
  
  for i, paper in enumerate(papers):

    with open(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()), 'a+') as output:
      output.write('\n\n' + '{:5}:'.format(i) + paper['title']
                    + ' (' + paper['arxivid'] + ')' + '\n')
      output.write(6 * ' ' + 'Authors: ' + paper['authors'] + '\n')
      output.write(6 * ' ' + 'Subjects:' + paper['categories'] + '\n')
      output.write(6 * ' ' + 'Comments:' + paper['comments'] + '\n\n')
      output.write(paper['abstract'] + '\n\n')
      output.write('---------------------------------------------------------------------')

def send_email(color, from_email=EMAIL, from_password=EMAIL_LOGIN, to_email=EMAIL):

  if from_email is None:
    return 0

  try:
    with open(DOWNLOAD_PATH + '/digest-{}.txt'.format(date.today()), 'r') as output:
      message = output.read()
  except IOError:
    print(color.YELLOW + 'WARNING: Email will not be sent because message is empty.' + color.END)
    return 0
  
  email_data = MIMEText(message)
  email_data['Subject'] = 'arXiv Digest {}'.format(date.today())
  email_data['From'] = from_email
  email_data['To'] = to_email

  server = smtplib.SMTP('smtp.gmail.com', 587)
  server.ehlo()
  server.starttls()
  server.login(from_email, from_password)
  server.sendmail(from_email, to_email, email_data.as_string())
  server.close()

  return 0


if __name__ == '__main__':

  # ============================== Argument Parser ==============================

  if any([1 if arg in sys.argv else 0 for arg in ['-v', '--version']]):
    print(version)
    sys.exit(0)

  if any([1 if arg in sys.argv else 0 for arg in ['-h', '--help']]):
    name = os.path.basename(sys.argv[0])

    print('This is {}. Get your daily arXiv dose.'.format(name))
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

  try:
    config = config_read()
  except FileNotFoundError:
    color = Color(True)
    print(color.YELLOW + 'WARNING: ' + color.END + 'Configuration file not found. One will be generated from your choices below...')
    setup(color)
    config = config_read()  

  style = config['STYLE']
  color = Color(config['COLORED'] == 'y')
  cat_whitelist = [s.strip() for s in config['CATEGORY_WHITELIST'].split(';') if s != '']
  cat_blacklist = [s.strip() for s in config['CATEGORY_BLACKLIST'].split(';') if s != '']
  key_blacklist = [s.strip() for s in config['KEYWORD_BLACKLIST'].split(';') if s != '']

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

  print_to_terminal(papers, color)

  print_to_file(papers)

  send_email(color, from_email=from_address)

  # =============================================================================


  # ============================= Download Papers ======================+========

  download_list = download_prompt(len(papers), color)

  downloader(download_list, papers, style)

  # =============================================================================


