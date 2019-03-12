### Reason eveything is packed into function - I'm hosting this script on AWS Lambda
def sumnewsaz_lmbd(event, context):
    import bs4 as bs ### BeautifullSoup, parser
    import lxml ### Lambda required to add separately apparently
    import requests ### Request handling
    import re ### Regular expressions
    import pickle ### Pickling list to the file
    import feedparser ### RSS Feed reader
    import nltk ### Natural Langiage Toolkit, for main stuff
    from nltk.corpus import stopwords ### Stopwords = words that bear no important meaning
    from nltk.tokenize import word_tokenize, sent_tokenize ### Tokenizing words and sentences
    from nltk.stem.snowball import SnowballStemmer ### Keeping a stem of a word
    import telebot ### Well, Telegram API wrapper, obviously, duh
    import datetime ### For comparing time between runs, diagnostical
    import os ### File checking (if exists)
    import boto3 ### AWS S3 access
    import botocore ### Also AWS S3 access

    ### Time comparison stuff
    currentDT = datetime.datetime.now()
    final_print=''
    final_print=final_print+'********************'
    final_print=final_print+'\n'+'** '+str(currentDT.hour)+':'+str(currentDT.minute)+':'+str(currentDT.second)+' **'
    final_print=final_print+'\n********************'

    ### S3 file upload/download stuff
    ### The reason for '/tmp/' directory is because AWSLambda does not allow any other directory for file storage
    bucketName = "sumnewsaz" ### My bucket name
    KeyUp = "/tmp/init.nwdt" ### What to upload
    outPutnameUp = "init.nwdt" ### How to upload
    KeyDown = "init.nwdt" ### What to download
    outPutnameDown = "/tmp/init.nwdt" ### How to download

    s3 = boto3.resource('s3')

    ### !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ### !!! RUN TWO LINES BELOW THE FIRST TIME YOU RUN THIS SCRIPT !!!
    ### !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    ### Be ready that nltk may ask you to download something else - read any output 
    #nltk.download("stopwords")
    #nltk.download('averaged_perceptron_tagger')


    ############################################################################################################################################################
    ########################################################################
    ### The function below is presented to you by Doofensmirtz Evil Inc. ###
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
    ### The function above is presented to you by Doofensmirtz Evil Inc. ###
    ########################################################################
    ############################################################################################################################################################


    ### Create Telegram Bot Instance
    bot = telebot.TeleBot("MAH TOKEN")


    ###################################################################

    ### Empty some lists
    link_list=[] ### List of parsed links
    title_list=[] ### List of parsed titles
    universal_list=[] ### 2-D List contains both of the above
    old_list=[] ### Comparison for saving
    final_list=[] ### Also comparison for saving

    ### List of websites to parse, parse them collect links and news titles
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.122 Safari/537.36 Vivaldi/2.3.1440.60' ### Just in case
    news_list=['newssite1', 'newssite2', 'newssite3'] ### List of RSS Feeds
    i=0
    for urls in news_list:
        feedparser.USER_AGENT = user_agent
        feed = feedparser.parse(urls)
        for i, links in enumerate(feed.entries):
            if i<len(feed.entries)-2:
                missedItems=0
                link_list.append(feed.entries[i].link)
                title_list.append(feed.entries[i].title)



    ### Try to download file (if exists)
    s3 = boto3.resource('s3')
    try:
        s3.Bucket(bucketName).download_file(KeyDown, outPutnameDown)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            pass
        else:
            raise

    if os.path.isfile('/tmp/init.nwdt'): ### Check if file exists, if no file - create/download/create-download
       ### Load old link+titles from the init.nwdt file
        with open ('/tmp/init.nwdt', 'rb') as fp:
            old_list = pickle.load(fp) 
    else:
        ## If you need init.nwdt file creation from the scratch, saves stuff as two-dimensional list (array)
        universal_list.append(link_list)
        universal_list.append(title_list)
        with open('/tmp/init.nwdt', 'wb') as fp:
           pickle.dump(universal_list, fp)
        s3 = boto3.client('s3')
        s3.upload_file(KeyUp,bucketName,outPutnameUp) ### And upload fresh file
        ## Also load "old" link+titles from the newly created init.nwdt file
        with open ('/tmp/init.nwdt', 'rb') as fp:
            old_list = pickle.load(fp) 






    overall_links=len(link_list) ### Saving number of all parsed links

    ### Compare old list with new list, remove old links and titles from the new list to keep only the shit that freshhhhhh
    for i in old_list[0]:
        for ttl, j in enumerate(link_list):
            if i==j:
                link_list.pop(ttl)
                title_list.pop(ttl)

    fresh_links=len(link_list) ### Saving the number of fresh links only

    ### Terminal printing, for myself
    final_print=final_print+'\nFresh links'
    for index1, items in enumerate(link_list):
        final_print=final_print+'\n'+str(link_list[index1])+' - '+str(title_list[index1])


    ### Lists of filtration triggers
    trigger_words=[
        'кода доступа', 'кодом доступа', 'paid news', ### Remove trend.az paid news 
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


    ### Let's loop through the list of links, on each iteration we compile message as title+text+link and send it
    final_print=final_print+'\n-------------------------'
    final_print=final_print+'\nFiltered links'
    news_posted=0
    for index, links in enumerate(link_list):
        headers = {'user-agent': user_agent} ### Just in case
        ### Scraping some websites requires user-agent due to different "pRoTeCtIoNs" and shit
        message='*'+title_list[index]+'*'+Summarizinator3000(requests.get(links, headers=headers))+links
        ### Sort out all the useless shit these people publish:
        if any(trigger in message.lower() for trigger in trigger_words):
            continue
        if any(dayaz in message.lower() for dayaz in dayaz_specific) and 'day.az' in message.lower():
            continue
        if 'Day.Az представляет новость на азербайджанском языке' in message: ### Remove clearly important anouncement about news in native language
            message=message.replace('Day.Az представляет новость на азербайджанском языке ', '')
        if '\n\n\n' in message: ### Some news are so meaningless that summarizer empties the whole thing - remove those
            # print(message) ### Printing for myself, to see what got emptied
            continue
        final_print=final_print+'\n'+str(links)+' - '+str(title_list[index]) ### Printing for myself, again, fuck you
        news_posted+=1
        bot.send_message(chat_id, message, parse_mode='Markdown')




    ### Terminal printing, for myself, fuck you
    final_print=final_print+'\n\n-------------------------'
    final_print=final_print+'\nParse summary'
    final_print=final_print+'\nOverall links: '+str(overall_links)
    final_print=final_print+'\nFresh links: '+str(fresh_links)
    final_print=final_print+'\nNews posted after filtration: '+str(news_posted)
    ### Add new links and titles to the old list
    link_list.extend(old_list[0])
    title_list.extend(old_list[1])

    ### Create ultimate list to save back to the file
    final_list.append(link_list)
    final_list.append(title_list)

    ### To maintain file size, remove any items after 200th, if any
    if len(old_list[0])>200:
        n=len(old_list[0])-200
        del old_list[0][-n:]
        del old_list[1][-n:]

    ### Fucking save it all the same init.nwdt file and upload it fucks away to S3
    with open('/tmp/init.nwdt', 'wb') as fp:
        pickle.dump(final_list, fp)
    s3 = boto3.client('s3')
    s3.upload_file(KeyUp,bucketName,outPutnameUp)



    return(final_print)
###################################################################
