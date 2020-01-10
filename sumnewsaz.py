#!/usr/local/bin/python3.6
import bs4 as bs ### BeautifullSoup, parser
import lxml ### Lambda required to add separately apparently
import requests ### Request handling
import re ### Regular expressions
import feedparser ### RSS Feed reader
import nltk ### Natural Langiage Toolkit, for main stuff
from nltk.corpus import stopwords ### Stopwords = words that bear no important meaning
from nltk.tokenize import word_tokenize, sent_tokenize ### Tokenizing words and sentences
from nltk.stem.snowball import SnowballStemmer ### Keeping a stem of a word
import telebot ### Well, Telegram API wrapper, obviously, duh
import facebook ### Facebook SDK
import sqlite3 ### SQLite connection

### !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
### !!! UNCOMMENT THREE LINES BELOW THE FIRST TIME YOU RUN THIS SCRIPT !!!
### !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
### Be ready that nltk may ask you to download something else - read any output 
# nltk.download("stopwords")
# nltk.download('averaged_perceptron_tagger')
# nltk.download('punkt')

############################################################################################################################################################
########################################################################
### The function below is presented to you by Doofensmirtz Evil Inc. ###
########################################################################
########################################################################

def Summarizinator3000(scraped_data):

    ### Parse the page source, find all <p> tags, get all the text from them
    article = scraped_data.text
    parsed_article = bs.BeautifulSoup(article,'lxml')
    paragraphs = parsed_article.find_all('p')
    article_text = ""
    for p in paragraphs:
        article_text += " "+p.text

    ### Removing square brackets and extra spaces
    article_text = re.sub(r'\[[0-9]*\]', ' ', article_text)
    article_text = re.sub(r'\s+', ' ', article_text)

    if article_text=="":
        article_text="Paid news. Paid news." ### Protection from trend.az premium empty articles

    ### Removing special characters and digits
    formatted_article_text = re.sub('[^a-zA-Z]', ' ', article_text )
    formatted_article_text = re.sub(r'\s+', ' ', formatted_article_text)

    ### Define word stems, remove stopwords, tokenize the whole shit, in russian
    stemmer = SnowballStemmer("russian")
    stopWords = set(stopwords.words("russian"))
    words = word_tokenize(article_text)
    #nltk.data.path=("/nltk_data")

    ### Build the frequency table for the words in the whole article
    freqTable = dict()
    for word in words:
            word = word.lower()
            if word in stopWords:
                    continue
            word = stemmer.stem(word)

            if word in freqTable:
                    freqTable[word] += 1
            else:
                    freqTable[word] = 1

    ### Tokenize sentences and give them values depending on the words from above, build a dictionary with values
    sentences = sent_tokenize(article_text)
    sentenceValue = dict()
    for sentence in sentences:
            if sentence=='':
                sentence=' .' ### Protection against sometimes empty sentences, those result in divisionBy0 error in average value calculation
            for word, freq in freqTable.items():
                    if word in sentence.lower():
                            if sentence in sentenceValue:
                                    sentenceValue[sentence] += freq
                            else:
                                    sentenceValue[sentence] = freq


    sumValues = 0
    for sentence in sentenceValue:
            sumValues += sentenceValue[sentence]

    ### Average value of a sentence from original text
    average = int(sumValues / len(sentenceValue))

    ### Threshold, defined by how large is the original article
    if len(article_text)>7000:
        th=1.7
    elif len(article_text)>5000 & len(article_text)<7000:
        th=1.4
    elif len(article_text)>3000 & len(article_text)<5000:
        th=1.1
    elif len(article_text)>1000 & len(article_text)<3000:
        th=0.7
    elif len(article_text)>500 & len(article_text)<1000:
        th=0.2
    else:
        th=0

    ### Compile the summary text
    summary = ''
    for sentence in sentences:
            if (sentence in sentenceValue) and (sentenceValue[sentence] > (th * average)):
                    summary += " " + sentence



    ### Print summary
    #print(summary) ### Diagnostic backup
    if len(summary)>3500:
        summary=summary[:3000]+'...'
    summary="\n\n"+summary+"\n\n"

    return (summary)

########################################################################
########################################################################
### The function above is presented to you by Doofensmirtz Evil Inc. ###
########################################################################
############################################################################################################################################################


### Create Telegram Bot Instance
bot = telebot.TeleBot("MAH TOKEN")


###################################################################


### Lists of filtration triggers
trigger_words=[
    'кода доступа', 'кодом доступа', 'paid news', 'если вы являетесь зарегистрированным пользователем', 'свой логин' ### Remove trend.az paid news 
    '/weather/', 'hava', 'погод', 'градус', ### Remove weather news 
    'erotik', 'эроти', 'intim', 'интим', 'çılpa', 'əxla', 'qətiyyən', ### Remove day.az and oxu.az clickbait
    '/showbiz/', 'müğən', 'dəhşət', 'şok', 'güllə' ### Remove day.az and oxu.az clickbait
    '/casia/', '/scaucasus/', '/iran/', ### Remove trend.az news about Central Asia, South Caucasus, Iran
    '/unusual/', '/interesting/', '/interview/', '/tv/', '/criminal/', ### Remove overall useless news 
    '/hitech/', '/ict/', '/it/', '/tender/', ### Remove news about technology and such
    '/culture/', '/world/', '/life/', '/tourism/', '/energy/', '/business/finance' ### Remove overall mostly useless news
    '/sport', 'sport.day.az', '/auto-moto/', ### Remove sports news and oxu.az car news (?!)
    'day.az/society/', 'lady.day.az', ### Remove useless day.az news
    ]
dayaz_specific=['пашинян', 'армян', 'армен', 'paşin', 'trend', 'oxu.az', 'erməni', 'yerevan', 'ереван' ] ### Remove excessive news about Armenia and linked news from day.az

### Create DB
db_connection = sqlite3.connect('myrss.sqlite')
db = db_connection.cursor()
db.execute('CREATE TABLE IF NOT EXISTS magazine (title TEXT, date TEXT)')

### Checking if article is in database
def article_is_not_db(article_title, article_date):
    db.execute("SELECT * from magazine WHERE title=? AND date=?", (article_title, article_date))
    if not db.fetchall():
        return True
    else:
        return False

### Adding articles to the database
def add_article_to_db(article_title, article_date):
    db.execute("INSERT INTO magazine VALUES (?,?)", (article_title, article_date))
    db_connection.commit()

### Sites to parse + headers
news_list=['https://****.az/rss.php', 'https://www.****.az/feeds/index.rss', 'https://ru.****.az/feed', 'https://news.****.az/rss/all.rss'] 
user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.122 Safari/537.36 Vivaldi/2.3.1440.60' ### Just in case
headers = {'user-agent': user_agent}

### Facebook page access token, GraphAPI init, page ID declaration
page_access_token = "MAH TOKEN"
graph = facebook.GraphAPI(page_access_token)
facebook_page_id = "MAH PAGE ID"



### Let's summarize some shit and share it
def read_article_feed():
    for links in news_list:
      feedparser.USER_AGENT = user_agent
      feed = feedparser.parse(links)
      for article in feed['entries']:
          if article_is_not_db(article['title'], article['published']):
            message='*'+article['title']+'*'+Summarizinator3000(requests.get(article['link'], headers=headers))+article['link']
            if any(trigger in message.lower() for trigger in trigger_words):
                continue
            if any(dayaz in message.lower() for dayaz in dayaz_specific) and 'day.az' in message.lower():
                continue
            if 'Day.Az представляет новость на азербайджанском языке' in message: ### Remove clearly important anouncement about news in native language
                message=message.replace('Day.Az представляет новость на азербайджанском языке ', '')
            if '\n\n\n' in message: ### Some news are so meaningless that summarizer empties the whole thing - remove those
                continue
            bot.send_message(TELEGRAM_CHANNEL_ID, message, parse_mode='Markdown')
            graph.put_object(facebook_page_id, "feed", link=article['link'], message=message)
            ### print(article['title'], article['link'], article['published']) ### my impressive debugger
            add_article_to_db(article['title'], article['published'])

### Call everything and close DB connection
if __name__ == '__main__':
    read_article_feed()
    db_connection.close()
###################################################################

