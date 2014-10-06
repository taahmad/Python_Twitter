"""
Module: Module to get tweets.
Author: Tan Kok Hua

Requires:
    Twython
    Pandas (For further processing)

Learning:
    twitter function parameters
    https://dev.twitter.com/rest/reference/get/search/tweets

    Twython tutorial
    http://www.silkstream.net/blog/2014/06/retweeting-with-your-twython-twitter-bot.html

    using twitter keyword hacks (such as OR etc) in using OR or - to exclude kewyord

    Adv search with twitter
    https://support.twitter.com/articles/71577-using-advanced-search

    python twitter streamer
    http://www.kalisch.biz/2013/10/harvesting-twitter-with-python/

Limitations:
    Seems like the tweets limited to 7 days or 100 results (??)
    or do streaming and store the tweets?? --> need OAuth1

Updates:
    Oct 05 2014: Add in the stocktweetReader class.
               : Take care of situation where there is no data for the tweets.
               : Hav consolidated sweep for the different stocks in stocktweetReader.

TODO:
    Set alert functions.
    seems the info only for one month...
    remove the double quotes, user have to input double quote itself.
    need convert special character such as &
    Need to remove personal tweets such as I for stock (see any post processing suitable??)
    monitor and add in hash tag # stock if qty too high??

"""

import os, re, sys, time, datetime, copy, calendar
import pandas
from twython import Twython

class TweetsReader(object):
    """ Class to get tweets for specific objects"""
    def __init__(self, search_list, exclude_list = []):
        """ Initialize the class. Take in the search list and exclude list and manipulate it to fit to search paramters
            The API key and access token are read from file. User need to create and specify the files to read.
            Args:
                search_list (list): list of search key phrases. (joined with OR eg A OR B).
            Kwargs:
                exclude_list (list): list of phrases to exclude (joined with - eg -C). Default empty.
        """
        self.search_list = search_list
        self.exclude_list = exclude_list

        ## user parameters
        self.app_key_file = r'c:\data\key_info\twitter_api_key.txt' 
        self.token_file = r'c:\data\key_info\twitter_token.txt' # store in file for access token.
        self.__load_api_and_access_token()

        ## twitter object and parameters.
        self.twitter_obj = Twython(self.app_key, access_token=self.access_token)

        ## paramters for twitter objects
        ## temporary not used. Can be put in twython object search method.
        self.lang = 'en'
        self.result_type = 'mixed' #mixed, recent, popular
        self.result_count = 100 #max 100 per page, default 15
        #self.until ##for setting the date until YYYY-MM-DD

        ## form_search_str method
        self.twitter_search_query = ''
        self.form_seach_str_query() #form the search str at initialization

        ## Results storge
        self.search_results = [] # list of list with 1st item as date and 2nd item as results.
        self.tweet_count_per_search = []
        
    def __load_api_and_access_token(self):
        """ Load the access token from file in self.token_file.
            Set to self.access_token.
        """
        with open(self.app_key_file, 'r') as f:
            self.app_key = f.read()

        with open(self.token_file, 'r') as f:
            self.access_token = f.read()

    def set_search_list(self, search_list):
        """ Set new search list. Set to self.search_list.
            Args:
                search_list (list): new search list.
        """
        self.search_list = search_list

    def set_exclude_list(self, exclude_list):
        """ Set new exclude_list. Set to self.exclude_list.
            Args:
                exclude_list (list): new exclude_list
        """
        self.exclude_list = exclude_list

    def form_seach_str_query(self):
        """ Form the full query that is going to input to twitter object.
        """
        self.twitter_search_query = self.join_all_search_list() + ' ' + self.join_all_exclude_list()

    def join_all_search_list(self):
        """ Take all the items in self.search_list and concat it with "OR".
            Leave a space between items.
            For each item, treat it as one word so add the open and close quotes "".
            Returns:
                (str): concatenated str.
        """
        return " OR ".join(self.search_list)

    def join_all_exclude_list(self):
        """ Take all the items in self.exclude_list and concat it with "-".
            Leave a space for the previous item and no space for next item.
            For each item, treat it as one word so add the open and close quotes "".
            Returns:
                (str): concatenated str.
        """
        if self.exclude_list ==[]:
            return ''
        else:
            return '-' + " -".join(self.exclude_list)

    def set_num_result_to_retrieve(self, count):
        """ Set the twitter object number of results to return.
            Args:
                count (int): num of results.
        """
        self.result_count = count

    def convert_date_str_to_date_key(self, date_str):
        """ Convert the date str given by twiiter [created_at] to date key in format YYYY-MM-DD.
            Args:
                date_str (str): date str in format given by twitter. 'Mon Sep 29 07:00:10 +0000 2014'
            Returns:
                (int): date key in format YYYYMMDD
        """
        date_list = date_str.split()
        
        month_dict = {v: '0'+str(k) for k,v in enumerate(calendar.month_abbr) if k <10}
        month_dict.update({v:str(k) for k,v in enumerate(calendar.month_abbr) if k >=10})

        return int(date_list[5] + month_dict[date_list[1]] + date_list[2])

    def perform_twitter_search(self):
        """ Perform twitter search by calling the self.twitter_obj.search function.
            Ensure the setting for search such as lang, count are being set.
            Will store the create date and the contents of each tweets.
        """
        self.search_results = []
        tweets_search_status = self.twitter_obj.search(q=self.twitter_search_query,
                                         count= self.result_count)["statuses"]
        if tweets_search_status ==[]:
            print 'No data found for stock'
            return
        
        for n in tweets_search_status:
            # store the date
            date_key =  self.convert_date_str_to_date_key(n['created_at'])
            contents = n['text'].encode(errors = 'ignore')
            self.search_results.append([date_key, contents])

    def print_results(self):
        """ Print results."""
        for n in self.search_results:
            print 'Date: ', n[0]
            print n[1]
            print '-'*18

    def count_num_tweets_per_day(self, print_count =1):
        """ Count the number of tweets per day present. Only include the days where there are at least one tweets.
            Kwargs:
                print_count (bool): 1 - print results of count, 0 - no printing
        """
        self.tweet_count_per_search = []

        if self.search_results == []:
            return ## for no results

        day_info = [n[0] for n in self.search_results]
        date_df = pandas.DataFrame(day_info)
        grouped_date_info = date_df.groupby(0).size()
        date_group_data = zip(list(grouped_date_info.index), list(grouped_date_info.values))
        if print_count:
            for date, count in date_group_data:
                print date,' ', count

        self.tweet_count_per_search = date_group_data

## Additional functions for stock related.
class StockTweetsReader(TweetsReader):
    """
        Stock tweet class use primarily for stock tweet monitoring.
        iterate the various seach resutls based on primaary data set
        Add the quote to make the data more accurate.
        Args:
            stocklist (list): take in a list of stock to search for tweets.

        TODO:
            for the exclude list

    """
    def __init__(self, stocklist):
        super(StockTweetsReader, self).__init__([],[]) # initialize search list and exclude list to empty
        self.stocklist = stocklist

        ## modification of search list
        ## add more key terms to search item
        self.modified_part_search_list = ['','shares','stock', 'Sentiment', 'buy', 'sell']

        ## for setting indivdual stock handling.
        self.target_stock = ''

        ## combined output data.
        self.combined_tweet_results = dict() # split results by stock name
        self.combined_tweet_count = dict() # split tweet count by stock name
        
    def set_target_stock(self, stockname):
        """ Set individual target stock.
            Args:
                stockname (str): stock name to search for tweets.
        """
        self.target_stock = stockname

    def set_search_list_and_form_search_query(self):
        """ Set the search list for individual stocks.
            Set to self.search_list and self.twitter_search_query.
        """
        self.search_list = ['"' + self.target_stock + ' ' + n + '"'for n in self.modified_part_search_list]
        self.form_seach_str_query()

    def get_tweets_for_single_stock(self):
        """ Get tweets based on the search list of single stock.
        """
        print self.target_stock
        self.set_search_list_and_form_search_query()
        print self.twitter_search_query
        self.perform_twitter_search()
        #self.print_results()
        self.count_num_tweets_per_day(print_count =0)
        self.store_results()

    def store_results(self):
        """ Store the results for each of the stocks.
            Store to self.combined_tweet_count, self.combined_tweet_results
        """
        self.combined_tweet_count[self.target_stock] = self.tweet_count_per_search
        self.combined_tweet_results[self.target_stock] = self.search_results

    def iterate_results_for_all_stocks(self):
        """ Get the results for all stocks.
        """
        for n in self.stocklist:
            self.set_target_stock(n)
            self.get_tweets_for_single_stock()
            print '*'*18, '\n'

    def print_full_results(self):
        """ print the consolidated data set.

        """
        for n in self.combined_tweet_count.keys():
            print 'Processing stock: ', n
            for date, count in self.combined_tweet_count[n]:
                print date,' ', count
            
if __name__ == '__main__':

    """ Running the twitter 
    """
    
    choice = 3

    if choice ==1:
        search_list = ['apple','meat','kiwi',]
        exclude_list = ['orange','kok']

        hh = TweetsReader(search_list, exclude_list)
        print hh.twitter_search_query
        hh.perform_twitter_search()
        hh.print_results()
    
    if choice == 2:
        """Particularly for stocks. """
        ## group together or search each keyword one by one??
        search_list = ["Genting HK US$ sell" ]#, 'Nam cheong shares','Nam Cheong Sentiment', 'Nam Cheong buy', 'Nam Cheong sell']
        exclude_list = []

        hh = TweetsReader(search_list, exclude_list)
        print hh.twitter_search_query
        hh.perform_twitter_search()
        hh.print_results()
        print
        hh.count_num_tweets_per_day()

    if choice == 3:
        """Particularly for stocks. """
        ## group together or search each keyword one by one??
        import pandas
        stockfile = r'c:\data\full_oct02.csv'
        stock_df = pandas.read_csv(stockfile)
        stocklist = list(stock_df['NAME'])

        hh = StockTweetsReader(stocklist)
        hh.iterate_results_for_all_stocks()
        hh.print_full_results()




