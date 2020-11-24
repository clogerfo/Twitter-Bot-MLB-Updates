
import sys
from selenium import webdriver
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
from bs4 import BeautifulSoup as soup
import re
import time
import tweepy 
from tweepy import API
from tweepy import Cursor
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream

import creds

CONST_ARG = 3
CONST_SLEEP = 60


def connect_to_twitter():
    auth = OAuthHandler(creds.CONSUMER_KEY, creds.CONSUMER_SECRET)
    auth.set_access_token(creds.ACCESS_TOKEN, creds.ACCESS_TOKEN_SECRET)
    api = API(auth)
    return api

def connect_to_scoreboard(url):
	driver = webdriver.Chrome()
	driver.get(url)
	return driver

def sport_select(league):
	list_urls = ["http://www.espn.com/mlb/scoreboard", 
	"http://www.espn.com/nfl/scoreboard", "http://www.espn.com/nba/scoreboard"]
	for url in list_urls:
		if url.find(league) > -1:
			return url
			break


def format_tweet(data, player, twitter_account, info):

	string_space = "      "
	if len(player) > 6:
		space = len(player) - 6	
		for i in range(0, space):
			string_space = string_space + " "


	with open('temp.txt', 'w') as f:
		f.write("Player" + string_space)
		for i in info:
			f.write(i + '    ')
		f.write("\n")
		f.write(player + "     ")
		if len(info) == 5 :
			for d in data[2:7]:
				f.write(d.text + "         ")
		else:
			for d in data[1:8]:
				f.write(d.text + "         ")

	with open('temp.txt', 'r') as f:
		try:	
			twitter_account.update_status(f.read())
		except Exception as e:
			print("status duplicate")

	f.close()



def run_script(driver, twitter_account, team, batters_to_watch, pitchers_to_watch):

	status = ""

	while(status.find("Final") < 0):

		#Take html from site and apply BeautifulSoup's soup function
		innerHTML = driver.execute_script("return document.body.innerHTML")
		page_soup = soup(innerHTML, "html.parser")

		#games_wrap is array of every game on MLB scoreboard, must be reset.
		games_wrap = None
		games_wrap = page_soup.findAll('article',{'class':'scoreboard'})

		away = bot = False

		#Iterate through each game in the array of games
		for game in games_wrap:
			info = None
			game_id = game.get('id')
			box_url = '/mlb/boxscore?gameId=' + game_id
			info = game.find('tbody',{'id':'teams'})
			info = info.text.replace('\n','').replace('\t', '')

			#User-identified team not found in game, not a desired game.
			if info.find(team) == -1:
				pass

			else: 
				status = None
				status = game.find('th',{'class':'date-time'}).text

				#Split "info" string into array identifying the two competing teams
				teams = info.split('away')

				#Check if team is either home or away.
				if teams[0].find(team) > -1:
					away = True
				else:
					pass

				#Game is on-going, so we can pull live data.
				if status.find("Final") > -1:
					box_btn = driver.find_element_by_xpath('//a[@href="'
						+ box_url +'"]')
					box_btn.click()	

					time.sleep(5)

					box_html = driver.execute_script("return document.body.innerHTML")
					box_soup = soup(box_html, "html.parser")
					boxes = box_soup.findAll('div',{'class':'boxscore-2017__wrap'})

					index = 0
					if(away == False):
						index = 1

					#try/except to handle rare case of script exiting early. 
					try:
						box = boxes[index]
					except Exception as e:
						print("page format not supported")
						driver.close()

					#ESPN breaks down unique boxscores for pitchers and position players
					sub_box = box.findAll('article',{'class':'sub-module'})
					players = sub_box[0]
					pitchers = sub_box[1]

					"""
					Iterate throgh the box score table and tweet the line score
					for each player you identified as a player of interest
					"""
					for row in players.findAll('tr',{'class':
						'baseball-lineup__player-row'}):
						for player in batters_to_watch:
							if(row.find('td',{'class':'name'}).text.find(player) > -1):
								headers = ["ABs", "runs", "hits", "rbi", "walks"]
								format_tweet(row.findAll('td'), player, 
											twitter_account, headers)

					for row in pitchers.findAll('tr',{'class':
						'baseball-lineup__player-row'}):
						for player in pitchers_to_watch:
							if(row.find('td',{'class':'name'}).text.find(player) > -1):
								headers = ["Innings", "Hits", "Rs", "ERs", 
											"BBs", "Ks", "PC-st" ]
								format_tweet(row.findAll('td'), player, 
											twitter_account, headers)

					#The game is over and the script has completed. 
					driver.close()


				#Game is on-going, but inbetween innings
				#for loop must be exited because the html changes when game is inbetween innings.
				elif status[:3] == "End":
					break
					
				#Game is on-going, and either in the Top or Bottom half of the inning
				else:
					#Potential Error : IndexError: list index out of range
					#Script will correct itself on next pass
					try:
						players = game.find('div',{'class':'atBat'}).text.split()
						current_pitcher = players[2]
						current_batter = players[5]
					except Exception as e:
						print("BS exception caught, " + str(e))
					
		 			#Test to see if its the bottom or top of an inning
					if( status[:3] == 'Bot' ):
						bot = True	

					#Now check, is the team playing defense or offense. 
					if((away == False and bot == False) or 
						(away == True and bot == True)):	

						matchup_wrap = game.find('div',{'class':'atBat'})
						matchup = matchup_wrap.text.split()
						pitcher = matchup[1] + matchup[2]
						try:
							twitter_account.update_status("Team is pitching")
						except Exception as e:
							print("Tweepy exception caught, " + str(e))
					else:
						for batter in batters_to_watch:
							if(batter == current_batter):
						try:
							twitter_account.update_status("Team is batting")
						except Exception as e:
							print("Tweepy exception caught, " + str(e))
					
		time.sleep(CONST_SLEEP)
	



"""
script takes command line arguments in the following order :
Team name, num pitchers, num batters, list of batters, list of pitchers
command line examples:
python script.py Brewers 1 1 Cain Soria
python script.py Mets 3 2 Conforto McNeil Rosario deGrom Lugo
python script.py Yankees 2 2 Judge Stanton Severino 
"""

if __name__ == "__main__":

	if len(sys.argv) > CONST_ARG:
		print('Argument List:' + str(sys.argv))
		length_inputs = len(sys.argv)

		team = sys.argv[1]

		num_batters = int(sys.argv[2])
		num_pitchers = int(sys.argv[3])

		key_batters = sys.argv[4:4+num_batters]
		print(key_batters)
		key_pitchers = sys.argv[4+num_batters:length_inputs]
		print(key_pitchers)

		url = "http://www.espn.com/mlb/scoreboard"
		
		twitter_account = connect_to_twitter()
		web_driver = connect_to_scoreboard(url)

		run_script(web_driver, twitter_account, team, key_batters, key_pitchers)

	else:
		print("user arguments invalid, re-run script")





